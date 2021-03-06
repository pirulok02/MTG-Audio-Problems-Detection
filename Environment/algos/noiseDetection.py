from essentia.standard import HumDetector, NoiseBurstDetector, FrameGenerator
import numpy as np


def essHumDetector(x: list, Q0=.1, Q1=.55, frameSize=1024, hopSize=512, detectionThreshold=1,
                   sr=44100, minLength=None, percentageThrehold=80, timeWindow=None, minimumDuration=None, timeContinuity=None, numberHarmonics=None):
    """Computes the hum detection in x and computes a value over one of the path of the audio that has hum noise.
    
    Args:
        x: (list) input signal
        Q0: (float)
        Q1: (float) 
        detectionThreshold: (float)
        sr: (float) in Hz
        minLength: (int) in samples

    Returns:
        Percentage of the file whith hum noise
    """
    if not minLength:
        minLength = 10*sr
    # print(len(x), minLength)
    if len(x) < minLength:
        x = np.tile(x, int(np.ceil(minLength/len(x))))
    # print(len(x))
    frameSize = frameSize / sr
    hopSize = hopSize / sr
    if not minimumDuration:
        minimumDuration = frameSize / 4
    if not timeWindow:
        timeWindow = frameSize
    if not timeContinuity:
        timeContinuity = 10.0
    if not numberHarmonics:
        numberHarmonics = 1
    # print(minimumDuration, frameSize)
    if timeContinuity:
        _, _, _, starts, ends = HumDetector(Q0=Q0, Q1=Q1, frameSize=frameSize, hopSize=hopSize,
                                        detectionThreshold=detectionThreshold, sampleRate=sr,
                                        minimumDuration=minimumDuration, timeWindow=timeWindow, 
                                        timeContinuity=timeContinuity, numberHarmonics=numberHarmonics)(x)
    # print(starts,ends)

    dur = []
    for s, e in zip(starts, ends):
        dur.append(e-s)

    percentage = round(100*sum(dur)/len(x), 2)
    # len_x = len(x)
    # del starts; del ends; del _; del x
    return percentage, percentage > percentageThrehold


def essNoiseburstDetector(x: list, frameSize=1024, hopSize=512, detectionThreshold=0.05, percentageThrehold=5, **kwargs):
    """Computes the hum detection in x and computes a value over one of the path of the audio that has hum noise.
    
    Args:
        x: (list) input signal
        frameSize: (int) frame size for the analysis in Noise Burst Detector
        hopSize: (int) hopSize for the analysis in Noise Burst Detector
        detectionThreshold: (float)

    Returns:
        Part over one of the file whith hum noise
    """
    noiseBurstDetector = NoiseBurstDetector(**kwargs)

    idxs = []
    count = 0
    total = 0
    for i, frame in enumerate(FrameGenerator(x, frameSize=frameSize, hopSize=hopSize, startFromZero=True)):
        corrupt_samples = noiseBurstDetector(frame)
        corrupt_samples = hopSize * i + corrupt_samples

        if len(corrupt_samples) > int(detectionThreshold*frameSize):
            count += 1
            for s in corrupt_samples:
                idxs.append(s)
        total += 1

    percentage = round(100*count/total, 2)
    # del noiseBurstDetector_algo; del frame; del corrupt_samples; del x;
    return idxs, percentage, percentage > percentageThrehold
