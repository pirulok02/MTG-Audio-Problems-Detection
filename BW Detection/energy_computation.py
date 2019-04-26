import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import argparse
import essentia.standard as estd
import scipy.signal
from scipy.interpolate import interp1d
from essentia import array as esarr
eps = np.finfo("float").eps

def is_power2(num:int):
	"""States if a number is a positive power of two

	Args:
		num: int to be ckecked

	Returns:
		(bool) True if is power of 2 false otherwise
	"""
	return num != 0 and ((num & (num - 1)) == 0)

def normalise(sig:list, log=False):
	"""Normalises the values in a list

	Args:
		sig: iterable containing the values

	KWargs:
		log: (boolean) True if the list contains values in dB, False otherwise

	Returns:
		normalised list
	"""
	return np.array(sig) / max(sig) if not log else (np.array(sig) - max(sig))

def get_peaks(sig:list, xticks:list):
	"""Returns the x,y values of the peaks in sig

	Args:
		sig: numpy.array of the signal of which to fing the peaks
		xticks: numpy.array of the corresponding x axis values for sig

	Returns:
		yval: y values of the peaks
		xval: x values of the peaks
	"""

	if len(sig) != len(xticks):
		raise ValueError("xticks and sig must have the same length")

	peaks, _ = scipy.signal.find_peaks(sig) #get the index values of the local maxima of sig

	tuplelist = [(a, b) for a, b in zip(xticks[peaks], sig[peaks])]
	tuplelist.sort(key=lambda x: x[1], reverse=True)

	xval = [a for a, b in tuplelist]
	yval = [b for a, b in tuplelist]

	return xval, yval

def modify_floor(sig:list, floor_db:float, log=False):
	
	if log:
		sig[sig < (max(sig) + floor_db)] = max(sig) + floor_db
		return sig
	else:
		floor = 10 ** (floor_db/20)
		sig[sig < (max(sig) * floor)] = max(sig) * floor
		return sig

def compute_spectral_envelope(frame_fft:list, xticks:list, kind="linear"):
	"""Compute the spectral envelope through a peak interpolation method

	Args:
		frame_fft: (list) iterable with the mono samples of a frame
		xticks: (list) xticks of the frame
	
	Kwargs:
		kind: (str) Specifies the kind of interpolation as a string 
			(‘linear’, ‘nearest’, ‘zero’, ‘slinear’, ‘quadratic’, ‘cubic’, 
			‘previous’, ‘next’, where ‘zero’, ‘slinear’, ‘quadratic’ and 
			‘cubic’ refer to a spline interpolation of zeroth, first, 
			second or third order; ‘previous’ and ‘next’ simply return the 
			previous or next value of the point) or as an integer specifying 
			the order of the spline interpolator to use. (Default = ‘linear’).

	Returns:
		(list) of the same length as frame_fft and xticks containing the 
			interpolated spectrum.
	"""
	xp, hp = get_peaks(frame_fft, xticks) #compute the values of the local maxima of the function
	xp = np.append(xp,xticks[-1]) ; xp = np.append(0,xp) #appending the first value and last value in xticks
	hp = np.append(hp,frame_fft[-1]) ; hp = np.append(frame_fft[0],hp) #appending the first and last value of the function
	return interp1d(xp,hp,kind=kind)(xticks) #interpolating and returning

def compute_histogram(idx_arr:list, xticks:list, mask = []):
	"""Computes the histogram of an array of ints

	Args:
		idx_arr: (iterable) with int values
		f: (iterable)x index array for the histogram
	
	KWargs:
		mask: (iterable) int binary array

	Returns:
		hist: histogram
	"""

	idx_arr = [int(item) for item in idx_arr]
	if len(mask) == 0:
		hist = np.zeros(len(xticks))
		for idx in idx_arr:
			hist[idx] += 1
		return hist
	else:
		hist = np.zeros(len(xticks))
		if len(mask) != len(idx_arr): raise ValueError("Inconsistent mask size")
		for idx, boolean in zip(idx_arr, mask):
			if boolean:
				hist[idx] += 1
		return hist

def compute_mean_fc(fc_index_arr:list, xticks:list, SR:float, hist=[]):
	"""computes the most possible fc for that audio file

	Args:
		fc_index_arr: iterable with the predicted fc's per frame
		xticks: iterable containing the bin2f array
		SR: (float) Sample Rate
	
	Returns:
		most_likely_f: (float) frequency corresponding to the highest peak in the histogram
		conf: (float) confidence value between 0 and 1
		(bool): True if the file is predicted to have the issue, False otherwise
	"""
	if len(hist)==0:
		hist = compute_histogram(fc_index_arr, xticks) #computation of the histogram
	
	#fig,ax = plt.subplots(3,1,figsize=(15,9))
	most_likely_bin = np.argmax(hist) #bin value of the highest peak of the histogram

	#the confidence value changes depending on if most_likely_bin falls under the 90% lower spectrogram or not
	if most_likely_bin <= .85*len(hist):
		#if it falls under the 90% lower, the confidence is computed by a weighted sum of the values of the histogram,
		#the highest peak having the highest importance and decreasing as the indexes go further.

		#creation of the confidence scale
		#ax[0].stem(hist)
		conf_scale = abs(most_likely_bin - np.arange(len(hist))); conf_scale = max(conf_scale) - conf_scale ; conf_scale = conf_scale / max(conf_scale)
		#ax[1].stem(conf_scale)
		conf = sum(hist * conf_scale) / sum(hist) #computation of the confidence sum, normalised by the histogram length
		#ax[2].stem(hist * conf_scale / sum(hist))
		#plt.show()
		#return the analog frequency corresponding to the bin, confidence value, and True if the confidence value is higher than 0.6
		return most_likely_bin, conf, conf>0.6
	else:
		#if it falls over the 90% mark, the confidence is computated by summing the square of the 3 samples of the histogram closer to the max
		#and compare it to the sum of all the values appended to the histogram.
		#ax[0].stem(hist)
		conf = sum(hist[int(.85*len(hist)):]**2)
		conf /= sum(hist**2)
		#plt.show()
		return most_likely_bin, conf, False

def detectBW(fpath:str, frame_size:float, hop_size:float, floor_db:float, oversample_f:int):
	
	if os.path.splitext(fpath)[1] != ".wav": raise ValueError("file must be wav") #check if the file has a wav extension, else: raise error
	if not is_power2(oversample_f): raise ValueError("oversample factor can only be 1, 2 or 4") #check if the oversample factor is a power of two

	#audio loader returns x, sample_rate, number_channels, md5, bit_rate, codec, of which only the first 3 are needed
	audio, SR = estd.AudioLoader(filename = fpath)()[:2]

	if audio.shape[1] != 1: audio = (audio[:,0] + audio[:,1]) / 2 #if stereo: downmix to mono
	
	frame_size *= oversample_f #if an oversample factor is desired, apply it

	fc_index_arr = []
	hist = np.zeros(int(frame_size/2+1))
	interpolated_spectrum = np.zeros(int(frame_size / 2) + 1) #initialize interpolated_spectrum array
	fft = estd.FFT(size = frame_size) #declare FFT function
	window = estd.Windowing(size=frame_size, type="hann") #declare windowing function
	avg_frames = np.zeros(int(frame_size/2)+1)

	max_nrg = max([sum(abs(fft(window(frame)))**2) for frame in 
				estd.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True)])

	for i,frame in enumerate(estd.FrameGenerator(audio, frameSize=frame_size, hopSize=hop_size, startFromZero=True)):
		
		frame = window(frame) #apply window to the frame
		frame_fft = abs(fft(frame))
		#print(sum(frame_fft**2))
		nrg = sum(frame_fft**2)

		if nrg >= 0.1*max_nrg:
			frame_fft = frame_fft / np.sqrt(nrg)
			#print(sum(frame_fft**2))
			for i in range(len(frame_fft)):
				#print(sum(frame_fft[:i]**2))
				if sum(frame_fft[:i]**2) >= 0.99999:
					#print(i)
					#fc_index_arr.append(i)
					hist[i] += nrg
					break
			avg_frames = avg_frames + frame_fft
	
	if len(fc_index_arr): fc_index_arr.append(int(frame_size/2)+1)
	
	most_likely_bin, conf, binary = compute_mean_fc(fc_index_arr, np.arange(int(frame_size/2)+2), SR, hist=hist)
	print(most_likely_bin, conf, binary)
	#hist = compute_histogram(fc_index_arr, np.arange(int(frame_size/2)+2))
	avg_frames /= (i+1)
	#assert False
	print("f={}".format(str(most_likely_bin*SR / frame_size)))
	fig, ax = plt.subplots(2,1,figsize=(15,9))
	ax[0].plot(20 * np.log10(avg_frames + eps))
	ax[0].axvline(x=np.argmax(hist), color = 'r')
	ax[1].stem(hist)
	plt.show()

	#frame_fft_db = 20 * np.log10(frame_fft + eps) #calculate frame fft values in db

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Calculates the effective BW of a file")
	parser.add_argument("fpath", help="relative path to the file")
	parser.add_argument("--frame_size", help="frame_size for the analysis fft (default=256)",default=256,required=False)
	parser.add_argument("--hop_size", help="hop_size for the analysis fft (default=128)",default=128,required=False)
	parser.add_argument("--floor_db", help="db value that will be considered as -inf",default=-90,required=False)
	parser.add_argument("--oversample", help="(int) factor for the oversampling in frequency domain. Must be a power of 2",default=1,required=False)
	args = parser.parse_args()
	detectBW(args.fpath, args.frame_size, args.hop_size, args.floor_db, int(args.oversample))
