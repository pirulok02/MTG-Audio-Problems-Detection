from essentia.standard import FalseStereoDetector, StereoDemuxer, FrameGenerator, StereoMuxer


def falsestereo_detector(x: list, frame_size=1024, hop_size=512, correlationthreshold=0.98):
    """Computes the correlation and consideres if the information in the two channels is the same
    
    Args:
        x: (list) input signal

    Returns:
        final_bool: (bool) True if the information is the same in both channels, False otherwise
        percentace: (float) How many frames were false stereo over all the frames
    """
    rx, lx = StereoDemuxer()(x)

    lfg = FrameGenerator(lx, frameSize=frame_size, hopSize=hop_size, startFromZero=True)
    rfg = FrameGenerator(rx, frameSize=frame_size, hopSize=hop_size, startFromZero=True)

    mux = StereoMuxer()

    total = 0
    count = 0

    falseStereoDetector = FalseStereoDetector()

    for frameL, frameR in zip(lfg, rfg):
        if falseStereoDetector(mux(frameL, frameR))[0] > correlationthreshold:
            count += 1
        # frame_bool, _ = estd.FalseStereoDetector()(frame)
        # if frame_bool == 1: count += 1
        total += 1

    falseStereoDetector.reset()
    percentage = 100*count/total
    
    return percentage > 90.0, round(percentage, 2)


def outofphase_detector(x: list, frame_size=1024, hop_size=512, correlationthreshold=-0.8):
    """Computes the correlation and flags the file if the file has a 90% of frames out of phase
    
    Args:
        x: (list) input signal

    Returns:
        final_bool: (bool) True if the information is the same in both channels, False otherwise
        percentace: (float) How many frames were false stereo over all the frames
    """
    rx, lx = StereoDemuxer()(x)

    lfg = FrameGenerator(lx, frameSize=frame_size, hopSize=hop_size, startFromZero=True)
    rfg = FrameGenerator(rx, frameSize=frame_size, hopSize=hop_size, startFromZero=True)

    mux = StereoMuxer()

    total = 0
    count = 0
    falseStereoDetector = FalseStereoDetector()

    for frameL, frameR in zip(lfg, rfg):
        if falseStereoDetector(mux(frameL, frameR))[1] < correlationthreshold:
            count += 1
        total += 1

    falseStereoDetector.reset()
    percentage = 100*count/total
    finalBool = percentage > 90.0
    
    return finalBool, round(percentage, 2)
