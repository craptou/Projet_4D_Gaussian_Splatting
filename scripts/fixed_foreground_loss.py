"""Optional foreground L1 term; validation images never supply training masks."""
import math


def foreground_l1(prediction,target,cameras,weight):
    import torch
    if not math.isfinite(weight) or weight<=0:raise ValueError('Invalid foreground weight')
    if prediction.shape!=target.shape or len(cameras)!=len(prediction):
        raise ValueError('Loss batch shape mismatch')
    errors=(prediction-target).abs()
    extra=[]
    for error,camera in zip(errors,cameras):
        mask=camera.mask
        if mask is None:
            extra.append(error.new_zeros(()));continue
        mask=mask.to(device=error.device,dtype=torch.bool)
        if mask.shape!=error.shape[-2:] or not mask.any():raise ValueError('Invalid foreground mask')
        extra.append(error[:,mask].mean())
    return errors.mean()+weight*torch.stack(extra).mean()


def instrument_training(text):
    anchor='Ll1 = l1_loss(image_tensor, gt_image_tensor[:,:3,:,:])'
    if text.count(anchor)!=1:raise ValueError('Pinned upstream loss anchor differs; refusing instrumentation')
    return text.replace(anchor,'Ll1 = foreground_l1(image_tensor, gt_image_tensor[:,:3,:,:], viewpoint_cams, foreground_weight)')
