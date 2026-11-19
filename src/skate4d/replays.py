"""Candidate replay alignment from a visible UI slider, independent of scene motion."""
from statistics import median


def slider_center(pixels, width, height):
    """Locate a bright knob relative to its local background in a 16px-high strip."""
    if height != 16 or len(pixels) != width * height:
        raise ValueError("Slider strip must be exactly 16 pixels high")
    runs = []
    for x in range(width):
        inside = sum(pixels[y*width+x] for y in (4, 5, 9, 10))/4
        outside = sum(pixels[y*width+x] for y in (0, 1, 14, 15))/4
        if inside-outside > 35:
            if not runs or x != runs[-1][-1]+1:
                runs.append([x])
            else:
                runs[-1].append(x)
    candidates = [run for run in runs if 14 <= len(run) <= 32]
    if not candidates:
        return None
    run = max(candidates, key=len)
    return (run[0]+run[-1])/2


def passage_boundaries(trace, jump=100):
    boundaries = [0]
    previous = None
    for i, x in enumerate(trace):
        if x is None:
            continue
        if previous is not None and previous-x > jump:
            boundaries.append(i)
        previous = x
    return boundaries + [len(trace)]


def fit_passage(trace, start, end, low, high, fps):
    """Robust linear cursor fit; reject short/incomplete/nonuniform candidate passes."""
    points = [(i, trace[i]) for i in range(start, end)
              if trace[i] is not None and low-5 <= trace[i] <= high+5]
    if len(points) < 20:
        raise ValueError("Too few reliable slider observations")
    slopes = [(b[1]-a[1])/(b[0]-a[0]) for a in points[::3] for b in points[::3]
              if b[0]-a[0] >= 20 and 0.5 <= (b[1]-a[1])/(b[0]-a[0]) <= 6]
    if not slopes:
        raise ValueError("No coherent forward replay motion")
    slope = median(slopes)
    intercept = median(x-slope*i for i,x in points)
    inliers = [(i,x) for i,x in points if abs(x-(slope*i+intercept)) <= 4]
    if len(inliers) < 20 or len(inliers)/len(points) < 0.8:
        raise ValueError("Unstable playback or unreliable slider detection")
    mi = sum(i for i,x in inliers)/len(inliers)
    mx = sum(x for i,x in inliers)/len(inliers)
    slope = sum((i-mi)*(x-mx) for i,x in inliers)/sum((i-mi)**2 for i,x in inliers)
    intercept = mx-slope*mi
    if slope <= 0:
        raise ValueError("Replay cursor is not moving forward")
    first, last = (low-intercept)/slope, (high-intercept)/slope
    if first < start or last >= end:
        raise ValueError("Candidate does not cover the complete requested replay interval")
    if min(x for i,x in inliers) > low+5 or max(x for i,x in inliers) < high-5:
        raise ValueError("Requested interval would extrapolate missing replay observations")
    residuals = sorted(abs(x-(slope*i+intercept)) for i,x in inliers)
    return {"first_frame": round(first), "end_frame_exclusive": round(last),
            "pixels_per_second": slope*fps, "inlier_fraction": len(inliers)/len(points),
            "p95_residual_pixels": residuals[int(0.95*(len(residuals)-1))],
            "estimated_alignment_frames": residuals[int(0.95*(len(residuals)-1))]/slope}
