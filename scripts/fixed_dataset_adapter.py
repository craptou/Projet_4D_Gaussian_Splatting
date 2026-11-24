"""Runtime-only loader for calibrated centered True Skate crops.

Uses the pinned upstream CameraInfo/SceneInfo interfaces; no upstream edits.
"""
import json
from pathlib import Path


def install():
    import numpy as np
    from PIL import Image
    import torch
    from scene.dataset_readers import CameraInfo, SceneInfo, fetchPly, getNerfppNorm, sceneLoadTypeCallbacks
    from utils.graphics_utils import focal2fov

    def read(path, llffhold=8):
        path = Path(path)
        manifest = json.loads((path/"manifest.json").read_text())
        width,height = manifest["image_resolution"]
        focal,cx,cy = manifest["intrinsics"]
        if not np.allclose([cx,cy],[width/2,height/2]):
            raise ValueError("The pinned renderer requires centered intrinsics")
        train,test = [],[]
        train_ids,test_ids = set(),set()
        for index, record in enumerate(manifest["frames"]):
            with Image.open(path/record["image_path"]) as image:
                if image.size != (width,height):
                    raise ValueError("Image dimensions differ from calibration")
                tensor = torch.from_numpy(np.array(image.convert("RGB"),dtype=np.float32)/255).permute(2,0,1)
            pose = np.array(record["world_to_camera"],dtype=np.float64)
            info = CameraInfo(uid=index, R=pose[:,:3].T, T=pose[:,3], FovX=focal2fov(focal,width),
                FovY=focal2fov(focal,height), image=tensor, image_path=str(path/record["image_path"]),
                image_name=f"{record['camera_id']}-{index}", width=width, height=height,
                time=record["time"], mask=None)
            if record["split"] == "train":
                train.append(info); train_ids.add(record["camera_id"])
            elif record["split"] == "test":
                test.append(info); test_ids.add(record["camera_id"])
            else:
                raise ValueError("Unexpected split")
        assert train_ids.isdisjoint(test_ids) and test_ids == {manifest["heldout_camera"]}
        assert train_ids == set(manifest["training_cameras"])
        cloud = path/"points3D_multipleview.ply"
        return SceneInfo(point_cloud=fetchPly(str(cloud)), train_cameras=train, test_cameras=test,
            video_cameras=test, nerf_normalization=getNerfppNorm(train), ply_path=str(cloud), maxtime=1.0)

    sceneLoadTypeCallbacks["MultipleView"] = read
