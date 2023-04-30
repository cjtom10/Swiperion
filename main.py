
from direct import showbase
from direct.showbase.ShowBase import ShowBase
from pandac.PandaModules import loadPrcFileData
loadPrcFileData("", "win-size 1280 768")
loadPrcFileData("", "sync-video t")
import sys
import time
import direct.directbase.DirectStart

from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject
from direct.showbase.InputStateGlobal import inputState
from panda3d.core import *
from panda3d.bullet import *

import math

from mouseLook import MouseLook
base.disableMouse()

ml = MouseLook()
ml.setMouseModeRelative(True)
ml.setCursorHidden(True)
ml.centerMouse = True
ml.mouseLookMode = ml.MLMOrbit
ml.disable()

# props = WindowProperties()
# props.setCursorHidden(True)
# props.setMouseMode(WindowProperties.M_relative)
# base.win.requestProperties(props)

# To revert to normal mode:


#~ base.accept("mouse2", ml.enable)
#~ base.accept("mouse2-up", ml.disable)
base.accept("wheel_up", ml.moveCamera, extraArgs = [Vec3(0, 1, 0)])
base.accept("wheel_down", ml.moveCamera, extraArgs = [Vec3(0, -1, 0)])

base.cam.node().getLens().setFov(70.0)

globalClock.setMode(globalClock.MLimited) 
globalClock.setFrameRate(120.0)

from kcc import PandaBulletCharacterController


class Game(DirectObject):

    def __init__(self):

    # now, x and y can be considered relative movements

        base.setBackgroundColor(0.1, 0.1, 0.8, 1)
        base.setFrameRateMeter(True)
        
        base.cam.setPos(0, -30, 20)
        base.cam.lookAt(0, 0, 0)

        ml.resolveMouse()
        
        # Input
        self.accept('escape', self.doExit)
        self.accept('space', self.doJump)
        self.accept('c', self.doCrouch)
        self.accept('c-up', self.stopCrouch)
        
        self.accept('control', self.startFly)
        self.accept('control-up', self.stopFly)
        
        inputState.watchWithModifiers('forward', 'w')
        inputState.watchWithModifiers('left', 'a')
        inputState.watchWithModifiers('reverse', 's')
        inputState.watchWithModifiers('right', 'd')
        inputState.watchWithModifiers('turnLeft', 'q')
        inputState.watchWithModifiers('turnRight', 'e')
        
        inputState.watchWithModifiers('run', 'shift')
        
        inputState.watchWithModifiers('flyUp', 'r')
        inputState.watchWithModifiers('flyDown', 'f')
        
        # Task
        taskMgr.add(self.update, 'updateWorld')
        
        # Physics
        self.setup()
        
        # _____HANDLER_____
    
    def doExit(self):
        self.cleanup()
        sys.exit(1)
    
    def doJump(self):
        self.character.startJump(3)
    
    def doCrouch(self):
        self.character.startCrouch()
    
    def stopCrouch(self):
        self.character.stopCrouch()
    
    def startFly(self):
        self.character.startFly()
    
    def stopFly(self):
        self.character.stopFly()
    
    def processInput(self, dt):
        self.speed = Vec3(0, 0, 0)
        omega = 0.0
        
        v = 5.0
        
        if inputState.isSet('run'): v = 15.0
        
        if inputState.isSet('forward'): self.speed.setY(v)
        if inputState.isSet('reverse'): self.speed.setY(-v)
        if inputState.isSet('left'):    self.speed.setX(-v)
        if inputState.isSet('right'):   self.speed.setX(v)
        
        if inputState.isSet('flyUp'):   self.speed.setZ( 2.0)
        if inputState.isSet('flyDown'):   self.speed.setZ( -2.0)
        
        if inputState.isSet('turnLeft'):  omega =  120.0
        if inputState.isSet('turnRight'): omega = -120.0

        self.character.setAngularMovement(omega)
        self.character.setLinearMovement(self.speed, True)

        if self.speed != Vec3(0,0,0):
         self.playerAngle = math.atan2(-self.speed.x, self.speed.y)
        self.playerM.setH(math.degrees(self.playerAngle))
        
    def update(self, task):
        dt = globalClock.getDt()
        
        self.processInput(dt)
        
        oldCharPos = self.character.getPos(render)
        self.character.setH(base.camera.getH(render))
        self.character.update() # WIP
        newCharPos = self.character.getPos(render)
        delta = newCharPos - oldCharPos

        
        self.world.doPhysics(dt, 4, 1./120.)
        

        char2cam = self.character.getY(base.cam)
        # print('char dist to cam:', char2cam) 
        base.camera.setY(self.character.getY())
        # ml.orbitCenter = self.character.getPos(render)
        # base.camera.setPos(base.camera.getPos(render) + delta)
        self.updatePlayer()
        return task.cont
        
    def cleanup(self):
        self.world = None
        self.worldNP.removeNode()
        
    def setup(self):
        self.worldNP = render.attachNewNode('World')

        # World
        self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
        self.debugNP.show()

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))
        self.world.setDebugNode(self.debugNP.node())

        # Ground
        shape = BulletPlaneShape(Vec3(0, 0, 1.0), 0)
        
        np = self.worldNP.attachNewNode(BulletRigidBodyNode('Ground'))
        np.node().addShape(shape)
        np.setPos(0, 0, 0)
        np.setCollideMask(BitMask32.allOn())
        
        cm = CardMaker('ground')
        cm.setFrame(-20, 20, -20, 20)
        gfx = render.attachNewNode(cm.generate())
        gfx.setP(-90)
        gfx.setZ(-0.01)
        gfx.setColorScale(Vec4(0.4))
        
        self.world.attachRigidBody(np.node())
        
        spirit = loader.loadModel('spirit.bam')
        spirit.reparentTo(render)

        #player setup 
        self.character = PandaBulletCharacterController(self.world, self.worldNP, 1.75, 1.3, 0.5, 0.4)
        self.character.setPos(render, Point3(0, 0, 0.5))
        self.playerM = Actor('models/player/player.bam',{
                                'walk': 'models/player/player_walking.bam',
                                'idle': 'models/player/player_Idle.bam'
        })
        self.playerM.reparentTo(self.character.movementParent)
        self.playerIdle = True
        self.playerAngle = 0

        X = 0.3
        Y = 4.0
        Z = 1.5
        
        stepsY = 1.5
        
        # shapesData = [
        #     dict(name = 'wall0', size = Vec3(X, Y, Z), pos = Point3(Y*2.0, -(Y + stepsY), Z), hpr = Vec3()),
        #     dict(name = 'wall1', size = Vec3(X, Y, Z), pos = Point3(Y*2.0, (Y + stepsY), Z), hpr = Vec3()),
            
        #     dict(name = 'wall4', size = Vec3(X, Y, Z), pos = Point3(Y, (Y*2.0 + stepsY - X), Z), hpr = Vec3(90, 0, 0)),
        #     dict(name = 'wall5', size = Vec3(X, Y, Z), pos = Point3(-Y, (Y*2.0 + stepsY - X), Z), hpr = Vec3(90, 0, 0)),
        #     dict(name = 'wall6', size = Vec3(X, Y, Z), pos = Point3(Y, -(Y*2.0 + stepsY - X), Z), hpr = Vec3(90, 0, 0)),
        #     dict(name = 'wall7', size = Vec3(X, Y, Z), pos = Point3(-Y, -(Y*2.0 + stepsY - X), Z), hpr = Vec3(90, 0, 0)),
            
        #     dict(name = 'ceiling', size = Vec3(Y, Y*2.0, X), pos = Point3(0, -(Y + stepsY - X), Z), hpr = Vec3(90, 0, 0)),
        #     dict(name = 'ceiling', size = Vec3(Y, Z, X), pos = Point3(-Z, (Y + stepsY - X), Z*2.0-X), hpr = Vec3(90, 0, 0)),
        #     dict(name = 'ceiling', size = Vec3(Y, Z, X), pos = Point3(Z, (Y + stepsY - X), Z*4.0-X), hpr = Vec3(90, 0, 0)),
            
        #     # CHANGE ROTATION TO TEST DIFFERENT SLOPES
        #     dict(name = 'slope', size = Vec3(20, stepsY+Y*2.0, X), pos = Point3(-Y*2.0, 0, 0), hpr = Vec3(0, 0, 50)),
        # ]
        
        # for i in range(10):
        #     s = Vec3(0.4, stepsY, 0.2)
        #     p = Point3(Y*2.0 + i * s.x * 2.0, 0, s.z + i * s.z * 2.0)
        #     data = dict(name = 'Yall', size = s, pos = p, hpr = Vec3())
        #     shapesData.append(data)
        
        # for data in shapesData:
        #     shape = BulletBoxShape(data['size'])
            
        #     np = self.worldNP.attachNewNode(BulletRigidBodyNode(data['name']))
        #     np.node().addShape(shape)
        #     np.setPos(data['pos'])
        #     np.setHpr(data['hpr'])
        #     np.setCollideMask(BitMask32.allOn())
            
        #     self.world.attachRigidBody(np.node())
        
        # shape = BulletSphereShape(0.5)
        # np = self.worldNP.attachNewNode(BulletRigidBodyNode('Ball'))
        # np.node().addShape(shape)
        # np.node().setMass(10.0)
        # np.setPos(13.0, 0, 5.0)
        # np.setCollideMask(BitMask32.allOn())
        # self.world.attachRigidBody(np.node())
        
        # shape = BulletBoxShape(Vec3(0.5))
        # np = self.worldNP.attachNewNode(BulletRigidBodyNode('Crate'))
        # np.node().addShape(shape)
        # np.node().setMass(10.0)
        # np.setPos(-13.0, 0, 10.0)
        # np.setCollideMask(BitMask32.allOn())
        # self.world.attachRigidBody(np.node())
        
        
        # shape = BulletBoxShape(Vec3(1, 1, 2.5))
        # self.ghost = self.worldNP.attachNewNode(BulletGhostNode('Ghost'))
        # self.ghost.node().addShape(shape)
        # self.ghost.setPos(-5.0, 0, 3)
        # self.ghost.setCollideMask(BitMask32.allOn())
        # self.world.attachGhost(self.ghost.node())
        
        # taskMgr.add(self.checkGhost, 'checkGhost')
        
    
    def lvlSetup(self):
        self.lvl = self.worldNP.attachNewNode('lvl')
        
    def updatePlayer(self):
        if self.character.isOnGround():
            if self.speed !=0:
                anim = 'walk'
            else: anim = 'idle'
            if self.playerM.getCurrentAnim()!=anim:    
                self.playerM.setPlayRate(1,anim )
                self.playerM.play(anim)
                # print('anim = ', anim, self.playerM.getCurrentAnim)
            else:
                return
    def checkGhost(self, task):
        pass
        # ghost = self.ghost.node()
        # for node in ghost.getOverlappingNodes():
        #     print ("Ghost collides with", node)
        # return task.cont
    # def updatePlayer(self):
        
    #     else:

    #         self.playerIdle = True

game = Game()
run()


