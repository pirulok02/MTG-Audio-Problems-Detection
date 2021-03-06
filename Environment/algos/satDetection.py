from essentia.standard import SaturationDetector, FrameGenerator


def essSaturationDetector(x: list, frameSize=1024, hopSize=512, percentageThrehold=5, **kwargs):
    """Breaks x into frames and computes the start and end indexes 
    
    Args:
        x: (list) input signal
        frameSize: (int) frame size for the analysis in Saturation Detector
        hopSize: (int) hopSize for the analysis in Saturation Detector
        percentageThrehold: (int)
    
    Kwargs:
        Same **kwargs than the ones for SaturationDetector

    Returns:
        starts: start indexes
        ends: end indexes
        percentage of frames with the issue
    """
    saturationDetector = SaturationDetector(frameSize=frameSize, hopSize=hopSize, **kwargs)

    ends = []
    starts = []
    count = 0
    total = 0
    for frame in FrameGenerator(x, frameSize=frameSize, hopSize=hopSize, startFromZero=True):
        frame_starts, frame_ends = saturationDetector(frame)

        for s in frame_starts:
            starts.append(s)
        for e in frame_ends:
            ends.append(e)
        if len(frame_starts) + len(frame_ends) != 0:
            count += 1
        total += 1

    percentage = round(100*count/total, 2)

    return starts, ends, percentage, percentage > percentageThrehold
