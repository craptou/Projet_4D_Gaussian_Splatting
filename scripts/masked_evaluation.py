"""Report unavailable foreground regions explicitly instead of producing empty-mask NaNs."""


def region_metrics(prediction,target,mask,minimum_pixels=21):
    import torch
    if prediction.shape!=target.shape or prediction.ndim!=4 or tuple(mask.shape)!=tuple(prediction.shape[-2:]):
        raise ValueError('Region/image dimensions differ')
    pixels=int(mask.sum())
    if pixels<minimum_pixels:return dict(mean_psnr_db=None,mae=None,available=False,pixels=pixels)
    error=(prediction-target)[:,:,mask]
    mse=(error**2).mean((1,2))
    return dict(mean_psnr_db=float((-10*torch.log10(mse)).mean()),mae=float(error.abs().mean()),available=True,pixels=pixels)
