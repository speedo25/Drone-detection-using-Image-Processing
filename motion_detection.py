# import the necessary packages
from tempimage.tempimage import TempImage
from picamera.array import PiRGBArray
from picamera import PiCamera
from PIL import Image
import io
import sys
import struct
import argparse
import warnings
import datetime
import dropbox
import imutils
import json
import time
import cv2
import socket
 
def send_msg(client, msg):
    
    msg = struct.pack('<L', len(msg)) + msg
    client.sendall(msg)
    
# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True,
	help="path to the JSON configuration file")
args = vars(ap.parse_args())
 
# filter warnings, load the configuration and initialize the Dropbox
# client
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
client = None
counter=1
# check to see if to connect to server
if conf["use_server"]:
	# connect to server and start the session authorization process
	client = socket.socket()
	#client.connect(('localhost', 8000))
	client.connect(('192.168.2.140', 8000))
	print("[SUCCESS] connected to server")

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))
 
# allow the camera to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])
avg = None
lastUploaded = datetime.datetime.now()
motionCounter = 0

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
	# grab the raw NumPy array representing the image and initialize
	# the timestamp and motion detected/motion not detected text
	frame = f.array
	timestamp = datetime.datetime.now()
	text = "Motion Not Detected"
 
	# resize the frame, convert it to grayscale, and blur it
	frame = imutils.resize(frame, width=1500)
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (21, 21), 0)
 
	# if the average frame is None, initialize it
	if avg is None:
		print("[INFO] starting background model...")
		avg = gray.copy().astype("float")
		rawCapture.truncate(0)
		continue
 
	# accumulate the weighted average between the current frame and
	# previous frames, then compute the difference between the current
	# frame and running average
	cv2.accumulateWeighted(gray, avg, 0.5)
	frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
	
	# threshold the delta image, dilate the thresholded image to fill
	# in holes, then find contours on thresholded image
	thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255,
		cv2.THRESH_BINARY)[1]
	thresh = cv2.dilate(thresh, None, iterations=2)
	cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
		cv2.CHAIN_APPROX_SIMPLE)
	cnts = cnts[0] if imutils.is_cv2() else cnts[1]
 
	# loop over the contours
	for c in cnts:
		# if the contour is too small, ignore it
		if cv2.contourArea(c) < conf["min_area"]:
			continue
 
		# compute the bounding box for the contour, draw it on the frame,
		# and update the text
		(x, y, w, h) = cv2.boundingRect(c)
		cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
		text = "Motion Detected"
             
	# draw the text and timestamp on the frame
	ts = timestamp.strftime("%A %d %B %Y %I:%M:%S%p")
	cv2.putText(frame, "Area Status: {}".format(text), (10, 20),
		cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
	cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
		0.35, (0, 0, 255), 1)
	# check to see if motion is detected in the area
	if text == "Motion Detected":
		# check to see if enough time has passed between uploads
		if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
			# increment the motion counter
			motionCounter += 1
 
			# check to see if the number of frames with consistent motion is
			# high enough
			if motionCounter >= conf["min_motion_frames"]:
				# verify if server should be used
				if conf["use_server"]:
					# write the image to temporary file
					t = TempImage()
					cv2.imwrite(t.path, frame)
 
					# upload the image to server and cleanup the temporary image
					print("[UPLOAD] {}".format(ts))
					path = "/{base_path}/{counter}.jpg".format(
					    base_path=conf["server_base_path"], counter=counter)
					
					send_msg(client, open(t.path, "rb").read())
					counter+=1
					t.cleanup()

				# update the last uploaded timestamp and reset the motion
				# counter
				lastUploaded = timestamp
				motionCounter = 0
				
	# otherwise, no motion is detected
	else:
		motionCounter = 0
		# check to see if the frames should be displayed to screen
	if conf["show_video"]:
		# display the camera feed
		cv2.imshow("Camera Feed", frame)
		key = cv2.waitKey(1) & 0xFF
 
		# if the `q` key is pressed, break from the loop
		if key == ord("q"):
                    break
 
	# clear the stream in preparation for the next frame
	rawCapture.truncate(0)
