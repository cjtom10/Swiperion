from turtle import Vec2D
from panda3d.core import InputDevice
from panda3d.core import TextPropertiesManager
from direct.gui.OnscreenText import OnscreenText
class GamepadInput:


    def __init__(self) -> None:
        # icons = loader.loadModel("../models/xbone-icons.egg")
        # mgr = TextPropertiesManager.getGlobalPtr()
        # for name in ["face_a", "face_b", "face_x", "face_y", "ltrigger", "rtrigger", "lstick", "rstick"]:
        #     self.graphic = icons.find("**/" + name)
        #     self.graphic.setScale(1.5)
        #     mgr.setGraphic(name, self.graphic)
        #     self.graphic.setPos((-10, 10,0))

        # self.lblAction = OnscreenText(
        #     text = "Action",
        #     fg=(-10,1,1,1),
        #     scale = .15)
        # self.lblAction.hide()
        #for left joystrick event
        self.stickEvent = False
        self.canStickEvent = True
        self.stickEventTriggered=False
        self.inputDelay = True #brief delay for left stick

        self.leftX=0
        self.leftY=0
        
        self.lt = False
        self.rt = False

        self.trigger_l = 0
        self.trigger_r = 0
        
        self.leftjoystick = False
     
            
        self.gamepad = None
        devices = base.devices.getDevices(InputDevice.DeviceClass.gamepad)
        if devices:
            self.connect(devices[0])

        self.accept("connect-device", self.connect)
        self.accept("disconnect-device", self.disconnect)
    
        self.accept("gamepad-dpad_up",self.spaceCheck, [self.player2, 'up'])
        self.accept("gamepad-dpad_down",self.spaceCheck, [self.player2, 'down'])
        self.accept("gamepad-dpad_left",self.spaceCheck, [self.player2, 'left'])
        self.accept("gamepad-dpad_right",self.spaceCheck, [self.player2, 'right'])

        self.accept("gamepad-rshoulder",self.rotateCam, [self.player2,'right'])
        self.accept("gamepad-lshoulder",self.rotateCam, [self.player2,'left'])
        
        self.accept('gamepad-face_x',self.move, [self.player2])
        self.accept('gamepad-face_a',self.strike, [self.player2])
        # button inputs reguler

        #if rtrigger value ---
        # self.accept("gamepad-back", exit)
        self.accept("gamepad-start", self.doExit)
        # self.accept("gamepad-face_x", self.doAttack)
        # self.accept("gamepad-face_a", self.doJump)
        # self.accept("gamepad-face_a-up", self.AUp)
        # self.accept("gamepad-face_b", self.doDodge)
        # # self.accept("gamepad-face_b-up", self.actionUp)
        # self.accept("gamepad-face_y",self.actionY)# self.action, extraArgs=["face_y", (-10,0,0)])
        # # self.accept("gamepad-face_y-up", self.actionUp)

        # self.accept("gamepad-lshoulder", self.actionlb)

        # # self.accept('gamepad-lshoulder', self.checkposition)
        # # self.accept('gamepad-lshoulder-up', self.deltapos)

        # # self.accept("gamepad-rshoulder", self.bicepbreak)
        # self.accept("gamepad-rshoulder", self.actionrb)

        # self.accept("gamepad-rstick", self.recenterCam)

        # self.gamepad = base.devices.getDevices(InputDevice.DeviceClass.gamepad)[0]
        # Abut = self.gamepad.findButton("rstick")
        self.trigger_l = self.trigger_r = 0
        if self.gamepad:
            self.trigger_l = self.gamepad.findAxis(InputDevice.Axis.left_trigger)
            self.trigger_r = self.gamepad.findAxis(InputDevice.Axis.right_trigger)
        
        # self.left_x = self.gamepad.findAxis(InputDevice.Axis.left_x) 
        # self.left_y = self.gamepad.findAxis(InputDevice.Axis.left_y) 

        # if Abutton.pressed:
        #     print('right stick')
    
    def connect(self, device):
        """Event handler that is called when a device is discovered."""

        # We're only interested if this is a gamepad and we don't have a
        # gamepad yet.
        if device.device_class == InputDevice.DeviceClass.gamepad and not self.gamepad:
            print("Found %s" % (device))
            self.gamepad = device

            # Enable this device to ShowBase so that we can receive events.
            # We set up the events with a prefix of "gamepad-".
            base.attachInputDevice(device, prefix="gamepad")

            # Hide the warning that we have no devices.
            # self.lblWarning.hide()

    def disconnect(self, device):
        """Event handler that is called when a device is removed."""

        if self.gamepad != device:
            # We don't care since it's not our gamepad.
            return

        # Tell ShowBase that the device is no longer needed.
        print("Disconnected %s" % (device))
        self.detachInputDevice(device)
        self.gamepad = None

        # Do we have any other gamepads?  Attach the first other gamepad.
        devices = self.devices.getDevices(InputDevice.DeviceClass.gamepad)
        if devices:
            self.connect(devices[0])
        else:
            # No devices.  Show the warning.
            self.lblWarning.show()

    # def ltUp(self):
    #     self.lt = False
    # def rtUp(self):
    #     self.rt = False
    # def actionLt(self):
    #     self.lt = True
    # def actionRt(self):
    #     self.rt = True
    # def joystickwatch(self):
    #     self.left_x = self.gamepad.findAxis(InputDevice.Axis.left_x) 
    #     self.left_y = self.gamepad.findAxis(InputDevice.Axis.left_y)
    #     self.right_x = self.gamepad.findAxis(InputDevice.Axis.right_x)
    #     self.right_y = self.gamepad.findAxis(InputDevice.Axis.right_y) 
    #     # print("X:",self.leftX, self.left_x.value,"Y:", self.leftY)
    #     leftStickX = round(self.left_x.value * 10)
    #     leftStickY = round(self.left_y.value * 10)
    #     self.leftValue = abs(leftStickX)+abs(leftStickY)
    #     if self.leftValue>10:
    #         self.leftValue=10

        

    #     # add input timer here?
    #     # print(self.leftX, self.leftY)
    #     # print(leftStickX) 
    #     # canstick = 
    #     # if self.leftjoystick==False:
    #     #     self.canStickEvent = True
    #     self.trigger_l = self.trigger_l
    #     self.trigger_r = self.trigger_r
    #     if abs(leftStickX) > 1 or abs(leftStickY) > 1:
    #         # print('no thius one')
    #         # self.stickEvent=True
            
    #         self.leftjoystick = True
    #         self.leftX = self.left_x.value
    #         self.leftY = self.left_y.value
    #         #account for noise
    #     else:
    #         # print('this one')
            
    #         self.leftjoystick=False
    #         self.leftX = leftStickX / 10
    #         self.leftY = leftStickY / 10
        
        

    # # # def action(self, button, pos):
    # # #     # Just show which button has been pressed.
    # # #     icons = loader.loadModel("../models/xbone-icons.egg")
    # # #     mgr = TextPropertiesManager.getGlobalPtr()
    # # #     for name in ["face_a", "face_b", "face_x", "face_y", "ltrigger", "rtrigger", "lstick", "rstick"]:
    # # #         self.graphic = icons.find("**/" + name)
    # # #         self.graphic.setScale(1.5)
    # # #         mgr.setGraphic(name, self.graphic)
    # # #         self.graphic.setPos((-10, 10,0))
    # # #     self.lblAction.text = "Pressed \5%s\5" % button
    # # #     self.graphic.setPos(pos)
    # # #     self.lblAction.show()

    # # # def actionUp(self):
    # # #     # Hide the label showing which button is pressed.
    # # #     self.lblAction.hide()
