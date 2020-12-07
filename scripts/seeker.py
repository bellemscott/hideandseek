#!/usr/bin/env python
import rospy, sys, math, tf, random
import cv2, cv_bridge, numpy
from std_msgs.msg import String
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image, LaserScan
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion

class Seeker: 

    def __init__(seeker):
        seeker.img_sub = rospy.Subscriber('/seeker/camera/rgb/image_raw', Image, seeker.img_callback)
        seeker.pub = rospy.Publisher('/seeker/cmd_vel', Twist, queue_size=1)
        seeker.scan_sub = rospy.Subscriber('/seeker/scan', LaserScan, seeker.scan_callback)
        seeker.odom_sub = rospy.Subscriber('/seeker/odom', Odometry, seeker.odom_callback)
        seeker.twist = Twist()
        seeker.yaw = seeker.roll = seeker.pitch = 0
        seeker.distanceX = 0
        seeker.distanceY = 0
        seeker.cv = cv_bridge.CvBridge()
        seeker.PI = 3.14
        seeker.count = 0
        seeker.turned = False
        seeker.regions_ = {           
            'right':0,
            'left':0,
            'fright':0,
            'front':0,
            'fleft':0
            }
        seeker.found = False
        cv2.namedWindow("Image_Window", cv2.WINDOW_NORMAL)
        cv2.namedWindow("band", cv2.WINDOW_NORMAL)

    # scan callback
    def scan_callback(seeker, msg):
        ranges = msg.ranges
        seeker.regions_ = {
            'right':  min(min(msg.ranges[60:92]), 10),
            'fright': min(min(msg.ranges[10:59]), 10),
            'front':  min(min(msg.ranges[0:10]), 10),
            'fleft':  min(min(msg.ranges[280:339]), 10),
            'left':   min(min(msg.ranges[270:300]), 10),
            }

    # odom callback 
    def odom_callback(seeker, msg):
        distanceX = msg.pose.pose.position.x
        distanceY = msg.pose.pose.position.y
        orientation = msg.pose.pose.orientation
        orientation_list = [orientation.x, orientation.y, orientation.z, orientation.w]
        (seeker.roll, seeker.pitch, seeker.yaw) = euler_from_quaternion(orientation_list)

    def chooseDirection(seeker, direction):
        turn = 0
        if direction == 1:
            turn = 0.5
        elif direction == 2:
            turn = 2.5
        elif direction == 3:
            turn = -0.785
        elif direction == 4:
            turn = -2.3
        seeker.turned = True 
        return turn
    
    def decider(seeker):
        regions = seeker.regions_
        d = 0.5
        d2 = 1.5
        if seeker.count%6 == 0 and regions['front'] > d and regions['fleft'] > d and regions['fright'] > d:
            print("turning in place")
            turn = 2.5
            while (seeker.yaw < turn):
                print(seeker.yaw)
                seeker.twist.linear.x = 0.0
                seeker.twist.angular.z = 0.5
                seeker.pub.publish(seeker.twist)
        elif regions['front'] < d and regions['right'] < d: # turn right
            print("turning right")
            seeker.twist.linear.x = 0.1
            seeker.twist.angular.z = seeker.PI/6 
        elif regions['front'] < d and regions['left'] < d: # turn left
            print("turning left")
            seeker.twist.linear.x = 0.1
            seeker.twist.angular.z = -(seeker.PI/6)           
        elif regions['fleft'] < d or regions['fleft'] == d or regions['left'] < d or regions['fright'] < d or regions['fright'] == d or regions['fright'] < d: # follow wall
            print("following the wall")
            seeker.twist.linear.x = 0.4
            seeker.twist.angular.z = 0.4
        elif regions['front'] > d and regions['fleft'] > d and regions['fright'] > d: # find wall
            print("find wall")
            seeker.twist.linear.x = 0.4
            seeker.twist.angular.z = 0.0
   
    # img callback
    def img_callback(seeker, msg):
        seeker.twist.linear.x = 0.3
        seeker.pub.publish(seeker.twist)
        # get image from camera(from msg) and encode it to bgr8, then convert this image to hsv
        image = seeker.cv.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        lower_black = numpy.array([0, 0, 0])
        upper_black = numpy.array([180, 255, 30])
        mask = cv2.inRange(hsv, lower_black, upper_black)

        moment = cv2.moments(mask)
        if moment['m00'] > 0:
            seeker.found = True 
            print('I FOUND YOU')
            seeker.twist.linear.x = 0.0
            seeker.twist.angular.z = 0.0
        else:
            print('hider not found yet')
            if seeker.turned == False:
                direction = random.randint(1,4)
                print(direction)
                turn = seeker.chooseDirection(3)
                if turn > 0:
                    while seeker.yaw < turn:
                        seeker.twist.angular.z = 0.3
                        seeker.pub.publish(seeker.twist)
                elif turn < 0:
                    while seeker.yaw > turn: 
                        seeker.twist.angular.z = -0.3  
                        seeker.pub.publish(seeker.twist)
            seeker.decider()
            seeker.count = seeker.count + 1

        seeker.pub.publish(seeker.twist)

        cv2.resizeWindow("Image_Window", 500, 500)
        cv2.resizeWindow("band", 500, 500)
        cv2.imshow("Image_Window", image)
        cv2.imshow("band", mask)
        cv2.waitKey(3)

print('Time to seek!')
rospy.init_node('seeker')
seeker = Seeker()
rospy.spin()