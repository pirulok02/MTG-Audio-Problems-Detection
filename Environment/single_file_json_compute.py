import os
import json
import argparse
import numpy as np
from essentia.standard import AudioLoader
from algos.satDetection import ess_saturation_detector
from algos.noiseDetection import ess_hum_detector, ess_noiseburst_detector
from algos.clickDetection import ess_click_detector
from algos.startstopDetection import ess_startstop_detector
from algos.phaseDetection import falsestereo_detector, outofphase_detector
from algos.bitdepthDetection import bit_depth_detector
from algos.bwdetection import detectBW
from algos.LowSNR import lowSNR_detector

from algos.LowSnrOOP import LowSnrDetector
from algos.bitDepthDetectionOOP import BitDepthDetector
from algos.bwDetectionOOP import BwDetection


def single_json_compute(audiopath, jsonFolder, print_flag=False):
    """Calls the audio_problems_detection algorithms and stores the result in a json file

    Args:
        audiopath: string containing the relative path for the audio file
        jsonFolder: string containing the relative path for the json folder
        print_flag: (boolean) True if a preview of the josn file is desired, False otherwise (default = False)

    Returns:
        json_dict: (dict) dictionary with the audio's features
    """
    # print(audiopath)
    if not os.path.exists(audiopath): 
        raise ValueError("Audio File does not exist")
    if not os.path.exists(jsonFolder):
        print(jsonFolder + " does not exist, defaulting to audiofolder: " + os.path.dirname(args.audiopath))
        jsonFolder = os.path.dirname(args.audiopath)
    
    # print("Essentia Modules installed:")
    # print(dir(estd))

    audio, sr, channels, _, br, _ = AudioLoader(filename=audiopath)()

    monoaudio = np.sum(audio, axis=1)/channels

    frameSize = int(1024)
    if len(monoaudio)/frameSize < 10:
        frameSize = int(2 ** np.ceil(np.log2(len(monoaudio)/10)))

    hopSize = int(frameSize/2)
    bitDepthContainer = int(br / sr / channels)

    filename = os.path.splitext(os.path.basename(audiopath))[0]

    Snr = LowSnrDetector(frameSize=frameSize, hopSize=hopSize)
    Bit = BitDepthDetector(bitDepth=bitDepthContainer, chunkLen=100, numberOfChunks=100)
    BandWidth = BwDetection()
    
    sat_starts, sat_ends, sat_perc = ess_saturation_detector(monoaudio, frame_size=frameSize, hop_size=hopSize)
    hum_perc = ess_hum_detector(monoaudio, sr=sr)
    clk_starts, clk_ends, clk_perc = ess_click_detector(monoaudio, frame_size=frameSize, hop_size=hopSize)
    nb_indexes, nb_perc = ess_noiseburst_detector(monoaudio, frame_size=frameSize, hop_size=hopSize)
    if len(monoaudio) > 1465:
        sil_perc = ess_startstop_detector(monoaudio, frame_size=frameSize, hop_size=hopSize)
    else:
        sil_perc = "Audio file too short"
    fs_bool, fs_perc = falsestereo_detector(audio, frame_size=frameSize, hop_size=hopSize)
    oop_bool, oop_perc = outofphase_detector(audio, frame_size=frameSize, hop_size=hopSize)

    snr, snr_bool = Snr(audio)
    extr_b, b_bool = Bit(audio)
    bw_fc, bw_conf, bw_bool = BandWidth(audio, sr)

    if print_flag:
        print("{0} data: \n \tfilename params: \n \tSample Rate:{1}Hz \n \tNumber of channels:{2} \n \tBit Rate:{3}".format(filename, sr, channels, br))
        print("\n \tLength of the audio file: {0} \n \tFrame Size: {1} \n \tHop Size: {2}".format(len(audio), frameSize, hopSize))
        print("Saturation: \n \tStarts length: {0} \n \tEnds length: {1} \n \tPercentage of clipped frames: {2}%".format(len(sat_starts), len(sat_ends), sat_perc))
        print("Hum: \n \tPercentage of the file with Hum: {}%".format(hum_perc))
        print("Clicks: \n \tStarts length: {0} \n \tEnds length: {1} \n \tPercentage of clipped frames: {2}%".format(len(clk_starts), len(clk_ends), clk_perc))
        print("Silence: \n \tPercentage of the file that is silence: {}%".format(sil_perc))
        print("FalseStereo: \n \tIs falseStereo?: {0} \n \tPercentage of frames with correlation==1: {1}%".format(fs_bool,fs_perc))
        print("OutofPhase: \n \tIs outofphase?: {0} \n \tPercentage of frames with correlation<-0.8: {1}%".format(oop_bool, oop_perc))
        print("NoiseBursts: \n \tIndexes length:{0} \n \tPercentage of problematic frames: {1}%".format(len(nb_indexes),nb_perc))
        print("BitDepth: \n \tExtracted_b:{0} \n \tProblem in file: {1}".format(extr_b, b_bool))
        print("Bandwidth: \n \tExtracted_cut_frequency: {0} \n \tConfidence: {1} \n \tProblem in file: {2}%".format(bw_fc, bw_conf, bw_bool))
        print("lowSNR: \n \tExtracted_snr: {0} \n \tProblem in file: {1}%".format(snr, snr_bool))
        print("________________________________________________________________________________________________________________________________________")

    info = {
        "Saturation": {"Start indexes": len(sat_starts), "End indexes": len(sat_ends), "Percentage": sat_perc},
        "Hum": {"Percentage": hum_perc},
        "Clicks": {"Start indexes": len(clk_starts), "End indexes": len(clk_ends), "Percentage": clk_perc},
        "Silence": {"Percentage": sil_perc},
        "FalseStereo": {"Bool": fs_bool, "Percentage": fs_perc},
        "OutofPhase": {"Bool": oop_bool, "Percentage": oop_perc},
        "NoiseBursts": {"Indexes": len(nb_indexes), "Percentage": nb_perc},
        "BitDepth": { "Bool": b_bool},
        "Bandwidth": { "Bool": bw_bool},
        "lowSNR": { "Bool": snr_bool}
        # "BitDepth": { "BitDepth": b_bool, "extracted": extr_b},
        # "Bandwidth": { "Bandwidth": bw_bool, "cutfrequency": bw_fc, "confidence": bw_conf},
        # "lowSNR": { "lowSNR": snr_bool, "SNR": snr}
    }

    jsonpath = os.path.join(jsonFolder, filename + ".json")
    with open(jsonpath, "w") as jsonfile:

        json_dict = info.copy()
        for problem in json_dict:
            if isinstance(json_dict[problem],dict):
                for feature in json_dict[problem]:
                    if feature == "Bool":
                        json_dict[problem]["Bool"] = str(json_dict[problem]["Bool"])

        json.dump(json_dict, jsonfile)
    
    return info


if __name__ == "__main__": 
    parser = argparse.ArgumentParser(description="Calls the audio_problems_detection algorithms and stores the result in a json file")
    parser.add_argument("audiopath", help="relative path to the audiofile")
    parser.add_argument("--jsonfolder", help="string containing the relative path for the json file", default="", required=False)
    parser.add_argument("--print_flag", help="boolean, True if it is desired to print the information, False otherwise", default=False, required=False)
    args = parser.parse_args()
    if args.jsonfolder == "":
        jsonfolder = os.path.dirname(args.audiopath)
        print("json folder is:", jsonfolder)
        single_json_compute(args.audiopath, jsonfolder, args.print_flag)
    else:
        single_json_compute(args.audiopath, args.jsonfolder, args.print_flag)