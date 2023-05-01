# from pandac.PandaModules import loadPrcFileData
# loadPrcFileData('', 'load-display tinydisplay')

from direct import showbase
from direct.showbase.ShowBase import ShowBase
from pandac.PandaModules import loadPrcFileData

loadPrcFileData('', 'win-size 1280 768')
loadPrcFileData('', 'sync-video t')
import math
import random
import sys
import time
from typing import List

import direct.directbase.DirectStart
from direct.actor.Actor import Actor
from direct.interval.ActorInterval import ActorInterval, LerpAnimInterval
from direct.interval.IntervalGlobal import Func, Parallel, Sequence, Wait
from direct.interval.LerpInterval import *
from direct.showbase.DirectObject import DirectObject
from direct.showbase.InputStateGlobal import inputState
from panda3d.ai import AIWorld
from panda3d.bullet import *
from panda3d.core import *

from enemy import Vessel
from mouseLook import MouseLook
from spirit import Spirit

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


# ~ base.accept("mouse2", ml.enable)
# ~ base.accept("mouse2-up", ml.disable)
base.accept('wheel_up', ml.moveCamera, extraArgs=[Vec3(0, 1, 0)])
base.accept('wheel_down', ml.moveCamera, extraArgs=[Vec3(0, -1, 0)])

base.cam.node().getLens().setFov(70.0)

globalClock.setMode(globalClock.MLimited)
globalClock.setFrameRate(120.0)

import simplepbr

from kcc import PandaBulletCharacterController


class Game(DirectObject):
    def __init__(self):

        # now, x and y can be considered relative movements
        pipeline = simplepbr.init()
        pipeline.use_normal_maps = True
        pipeline.use_occlusion_maps = True

        base.setBackgroundColor(0.1, 0.1, 0.8, 1)
        base.setFrameRateMeter(True)

        base.cam.setPos(0, -13, 7)
        base.cam.lookAt(0, 0, 0)

        ml.resolveMouse()

        # Input
        self.accept('escape', self.doExit)
        self.accept('space', self.doJump)
        self.accept('shift', self.doDodge)
        self.currentStrike = 0
        self.accept('mouse1', self.doAttack)
        self.accept('mouse3', self.doPrayer)  # , [self.currentStrike])
        # self.accept('c', self.doCrouch)
        # self.accept('c-up', self.stopCrouch)

        self.accept('control', self.startFly)
        self.accept('control-up', self.stopFly)

        inputState.watchWithModifiers('forward', 'w')
        inputState.watchWithModifiers('left', 'a')
        inputState.watchWithModifiers('reverse', 's')
        inputState.watchWithModifiers('right', 'd')
        inputState.watchWithModifiers('turnLeft', 'q')
        inputState.watchWithModifiers('turnRight', 'e')

        # inputState.watchWithModifiers('run', 'shift')

        inputState.watchWithModifiers('flyUp', 'r')
        inputState.watchWithModifiers('flyDown', 'f')

        # Task
        taskMgr.add(self.update, 'updateWorld')

        # Physics
        self.setup()

        self.atx = None   # keeping track of attacks for combo

        # _____HANDLER_____

    def doExit(self):
        self.cleanup()
        sys.exit(1)

    def doJump(self):

        if self.character.movePoints <= 0:
            print('out of mp')
            return
        if self.isAttacking == True:

            return
        if (
            self.character.movementState == 'attacking'
            and self.isAttacking == False
        ):
            self.finishAction()

        self.character.movePoints -= 1
        # self.character.currentAction = 'jump'
        # print('speed',self.speed,'airdir', self.character.airDir)
        # if self.speed != Vec3(0, 0, 0):
        self.character.airDir = self.speed
        # else:
        #     self.character.airDir = self.playerM.getQuat().getForward() * 5
        # print('angle',self.angle)
        if self.speed != Vec3(0, 0, 0):
            self.playerM.setH(self.angle)
        self.speed = 0
        self.character.startJump(3)
        print('jump')

        # print(self.angle)

        self.character.currentAction = None

    def doDodge(self):

        if self.character.movePoints <= 0:
            print('out of mp')
            return
        if self.isAttacking == True:
            return
        if (
            self.character.movementState == 'attacking'
            and self.isAttacking == False
        ):
            self.finishAction()
        if self.character.movementState in self.character.airStates:
            self.character.movePoints -= 1
        if self.speed != Vec3(0, 0, 0):
            self.playerM.setH(self.angle)
        self.character.dodgedir = self.playerM.getQuat().getForward() * 15
        self.speed = 0
        self.character.movementState = 'dodging'

        self.animSeq = Sequence()

    def doCrouch(self):
        self.character.startCrouch()

    def doAttack(self):
        print('attack no', self.currentStrike)
        if self.character.movementState in self.character.airStates:
            return
        # if self.currentStrike>=3:
        #     self.currentStrike =  1
        #     print('combo limit')
        # return
        # if self.character.movementState == 'attacking':
        if self.isAttacking == True:
            print('already attacking')
            if self.currentStrike > 1:
                self.attackQueued = True

            return
        if self.character.movementState == 'attacking':
            if self.animSeq != None:
                self.animSeq.pause()
                self.animSeq = None
            # else:

        if self.speed != Vec3(0, 0, 0):
            self.playerM.setH(self.angle)
        print('attacl no', self.currentStrike)
        # self.character.atkDir = self.playerM.getQuat().getForward() maybe set this during active frames

        # self.speed = 0
        self.isAttacking = True
        self.character.movementState = 'attacking'
        if self.currentStrike == 1:
            self.atkAnim('strike1', 4, 20,self.playerATKNode, self.handL, CollisionSphere(0,0,0,.5))
            self.currentStrike += 1
            return
        if self.currentStrike == 2:
            self.atkAnim('strike2', 4, 20,self.playerATKNode, self.handR, CollisionSphere(0,0,0,.5))
            self.currentStrike += 1
            return
        if self.currentStrike == 3:
            self.atkAnim('strike3', 4, 20,self.playerATKNode, self.handR, CollisionSphere(0,0,0,.5))
            self.currentStrike += 1
            #     return
        # if self.currentStrike==2:

    def doPrayer(self):
        if self.isAttacking == True:
            print('already attacking')

            return

        if self.character.movementState == 'attacking':
            if self.animSeq != None:
                self.animSeq.pause()
                self.animSeq = None
        if self.character.movementState == 'attacking':
            if self.animSeq != None:
                self.animSeq.pause()
                self.animSeq = None
        if self.speed != Vec3(0, 0, 0):
            self.playerM.setH(self.angle)
        self.isAttacking = True
        self.character.movementState = 'attacking'
        self.character.atkDir = 0
        no = random.randint(1, 2)
        self.atkAnim(
            f'prayer{no}',
            4,
            16,
            self.playerParrynode,
            self.playerM,
            CollisionSphere(0,0,3,2)
        )
        #     self.atkAnim('strike2', 4,8)
        #     self.currentStrike +=1
        #     return
        # if self.currentStrike==3:
        #     #  self.finishAction()
        #     #  self.isAttacking = True
        # #     self.character.movementState='attacking'
        #     self.atkAnim('strike2', 14,18)
        #     self.currentStrike +=1
        #     return

        #     def doSlashatk(self):
        # if self.atx!=None and len(self.atx) >=4:
        #     print('combo limit')
        #     return

        # # if self.character.movementState == 'dodging':

        # # if self.character.movementState in self.character.airstates:# also if air attacking
        #     # print('air attack x')
        #     # self.smashAttack()
        # if self.character.isAttacking == True and self.attackqueue>0:

        #     # if self.attackQueued==True:
        #     #     print('attack already queued')
        #     if self.attackQueued ==False:
        #         # print('queue attack x- do slash # ', self.attackqueue+1)
        #         self.qdatk = 'slash'
        #         self.attackQueued=True
        # else:
        #     # print('shouldnt get here if ur dodging....')
        #     self.slashAttack()

    # def queueStage(self,x, qud):
    #     self.attackqueue = x
    #     self.attackQueued = qud
    #     # if qud==True:
    #     #     self.attached = False
    def check4Queue(self):
        """if there is a queued attack, this will trigger it"""
        if self.character.movementState != 'attacking':
            self.character.movementState = 'attacking'
        if (
            self.attackQueued == True
        ):   # or self.character.movementState == 'dodging':

            # self.finish()
            # if type == 'slash':
            if self.currentStrike == 2:
                self.atkAnim('strike2', 4, 20, self.playerATKNode, self.handR, CollisionSphere(0,0,0,.5))
                self.isAttacking = True
                self.currentStrike += 1
                self.attackQueued = False
                return
            if self.currentStrike == 3:
                self.atkAnim('strike3', 4, 20,self.playerATKNode, self.handR, CollisionSphere(0,0,0,.5))
                self.isAttacking = True
                self.currentStrike += 1
                self.attackQueued = False
        else:
            return

    # def atkAnim(self,order,)
    def atkAnim(self, anim, activeFrame, bufferFrame, node, bone, shape):

        if self.animSeq is not None:  # end attack anim sequence
            if self.animSeq.isPlaying():
                self.animSeq.pause()

        def atkFalse():
            self.isAttacking = False

        a1 = self.playerM.actorInterval(
            anim, startFrame=0, endFrame=activeFrame
        )
        active = self.playerM.actorInterval(
            anim, startFrame=activeFrame + 1, endFrame=bufferFrame
        )
        buffer = self.playerM.actorInterval(
            anim, startFrame=bufferFrame + 1, endFrame=30
        )

        atkF = Func(atkFalse)
        fin = Func(self.finishAction)
        c4q = Func(self.check4Queue)

        hB = Func(self.attachHB, bone, node, shape)
        noHB = Func(self.detachHB, node)

        self.animSeq = Sequence(a1, hB,active, atkF, c4q, buffer,noHB, fin)
        self.animSeq.start()

    # def prayerAnim(self,anim):
    #     if self.animSeq is not None:#end attack anim sequence
    #             if self.animSeq.isPlaying():
    #                     self.animSeq.pause()

    #     a1 =self.playerM.actorInterval(anim,startFrame=0,endFrame = activeFrame)
    #     active = self.playerM.actorInterval(anim,startFrame=activeFrame+1,endFrame = bufferFrame)
    #     buffer = self.playerM.actorInterval(anim,startFrame=bufferFrame+1, endFrame=30)

    #     atkF = Func(atkFalse)
    #     fin = Func(self.finishAction)
    # # def attach(self,bone):

    #     if self.attached == False: #and self.hitcontact==False:
    #         # if self.character.state == "OF":

    #         self.hb(parent=bone, node = self.atkNode, shape=CollisionCapsule(0, .5, 0, 0, 0, 0, .5))
    #  if self.character.state == "mech":
    #  self.hb(parent=self.bladeL, node = self.atkNode, shape=CollisionCapsule(0, .5, 0, 0, 2, 0, 1))
    #  self.hb(parent=self.bladeR, node = self.atkNode, shape=CollisionCapsule(0, .5, 0, 0, 2, 0, 1))
    # def attach(self,bone):
       
    #     if self.attached == False: #and self.hitcontact==False:
        
           
    #        self.hb(parent=bone, node = self.atkNode, shape=CollisionCapsule(0, .5, 0, 0, 0, 0, .5))

    def attachHB(self, parent, node, shape, pos=(0, 0, 0), visible=True):
        """player hitboxes for attacks/parries"""
        # self.character.movementState = "attacking"

        ##
        # print(self.speed)
        # self.footR = self.charM.expose_joint(None, 'modelRoot', 'foot.R')
        # self.footL = self.charM.expose_joint(None, 'modelRoot', 'foot.L')
        HitB = CollisionCapsule(0, 0.5, 0, 0, 0, 0, 0.5)
        # self.footHB = self.foot.attachNewNode(CollisionNode('rightfoot'))
        node.reparentTo(parent)
        node.node().addSolid(shape)
        # node.setZ(-.2)
        node.setPos(pos)

        self.attached = True
        if visible == True:
            node.show()
        # self.speed /= 6
        # self.footHB.instanceTo(self.footL)

        # shape = BulletCapsuleShape(.5, 1)
        # self.rightfootHB.reparentTo(self.foot)
        # self.rightfootHB.setP(90)
        # self.rightfootHB.node().addShape(shape)
        # self.world.attachGhost(self.rightfootHB.node())
    def detachHB(self, node):
        node.node().clearSolids()
        self.attached = False

    def finishAction(self):
        self.atkQueue = None
        self.character.movementState = 'endaction'
        if self.animSeq != None:
            self.animSeq.pause()
            self.animSeq = None
        self.attackQueued = False

        if self.attached == True:
            self.detachHB(self.playerATKNode)
            self.detachHB(self.playerParrynode)
        

    #  self.currentStrike =1
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

        # if inputState.isSet('run'): v = 15.0

        if inputState.isSet('forward'):
            self.speed.setY(v)
        if inputState.isSet('reverse'):
            self.speed.setY(-v)
        if inputState.isSet('left'):
            self.speed.setX(-v)
        if inputState.isSet('right'):
            self.speed.setX(v)

        if inputState.isSet('flyUp'):
            self.speed.setZ(2.0)
        if inputState.isSet('flyDown'):
            self.speed.setZ(-2.0)

        if inputState.isSet('turnLeft'):
            omega = 120.0
        if inputState.isSet('turnRight'):
            omega = -120.0

        if (
            self.character.movementState in self.character.airStates
            or self.character.movementState in self.character.actionStates
        ):
            if (
                self.speed != 0
                and self.character.movementState == 'attacking'
                and self.isAttacking == False
            ):
                self.finishAction()
            # self.airDir= self.speed
            # self.speed.x /= 2
            # self.speed.y /=2
            # print('no inpuit')
            return

        self.character.setAngularMovement(omega)
        self.character.setLinearMovement(self.speed, True)

        # self.playerAngle = math.atan2(-self.speed.x, self.speed.y)

    def update(self, task):
        dt = globalClock.getDt()

        self.processInput(dt)

        # print('is attacking?', self.isAttacking)

        oldCharPos = self.character.getPos(render)
        self.character.setH(base.camera.getH(render))
        self.character.update()   # WIP
        newCharPos = self.character.getPos(render)
        delta = newCharPos - oldCharPos

        self.world.doPhysics(dt, 4, 1.0 / 120.0)

        char2cam = self.character.getY(base.cam)
        # print('char dist to cam:', char2cam)
        base.camera.setY(self.character.getY())
        # ml.orbitCenter = self.character.getPos(render)
        # base.camera.setPos(base.camera.getPos(render) + delta)
        self.updatePlayer()
        if self.character.movementState != 'attacking':
            self.currentStrike = 1
            # print('state attacking', self.isAttacking, self.currentStrike)
        # update enemy ai
        self.updateAi()
        self.updateSpirit()

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

        self.attackQueued = False
        self.attached = False

        # player setup
        self.character = PandaBulletCharacterController(
            self.world, self.worldNP, 1.75, 1.3, 0.5, 0.4
        )
        self.character.setPos(render, Point3(0, 0, 0.5))
        self.playerM = Actor(
            'models/player/player.bam',
            {
                'walk': 'models/player/player_walking.bam',
                'idle': 'models/player/player_idle.bam',
                'jump': 'models/player/player_JUMP.bam',
                'fall': 'models/player/player_FALL.bam',
                'land': 'models/player/player_land.bam',
                'dodge': 'models/player/player_dodge.bam',
                'strike1': 'models/player/player_strike1.bam',
                'strike2': 'models/player/player_strike2.bam',
                'strike3': 'models/player/player_strike3.bam',
                'prayer1': 'models/player/player_pray1.bam',
                'prayer2': 'models/player/player_pray2.bam',
            },
        )
        self.handR = self.playerM.expose_joint(None, 'modelRoot', 'Hand.R')
        self.handL = self.playerM.expose_joint(None, 'modelRoot', 'Hand.L')

        self.playerM.setScale(.5)
        self.playerM.reparentTo(self.character.movementParent)
        self.playerIdle = True

        self.isAttacking = False   # when this is false, dodges, movement, jumps end attack, asttacking
        self.angle = 0
        self.playerAngle = 0
        self.animSeq = None
        self.currentStrike = 1

        X = 0.3
        Y = 4.0
        Z = 1.5

        stepsY = 1.5

        self.collisionSetup()

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

        # enemy setup
        # spawn spirit
        self.spirit = Spirit(self.world, self.worldNP, self.playerM)
        # ai
        self.aiWorld = AIWorld(self.worldNP)
        # spawn vessels
        self.vessels: List[Vessel] = []
        for i in range(10):
            self.vessels.append(
                Vessel(
                    taskMgr,
                    f'vessel{i}',
                    self.worldNP,
                    self.world,
                    self.aiWorld,
                    self.playerM,
                    i > 7,
                )
            )

    def lvlSetup(self):
        self.lvl = self.worldNP.attachNewNode('lvl')

    def updatePlayer(self):
        # if self.character.currentAction!=None:
        #     return
        # print('anf',self.angle)
        # print('mvtstate', self.character.movementState)
        # currentAnim= self.playerM.getCurrentAnim()
        # if self.character.movementState in self.character.airStates:
        #     self.character.movementState == "jumping":
        #         if(currentAnim)!="jump":
        # print(self.character.movementState)
        if self.character.isOnGround() and self.character.movePoints!=3:
            self.character.movePoints=3

        # set angle here
        self.angle = (
            math.degrees(math.atan2(-self.speed.x, self.speed.y))
        ) % 360
        # self.angle = self.angle % 360
        h = self.playerM.getH() % 360

        def interAngle(angle):
            # interpolates player angle
            self.angle = math.degrees(angle)
            self.angle = self.angle % 360
            h = self.playerM.getH() % 360

            # print(self.playerAngle,abs(self.playerAngle-self.angle))
            if abs(self.playerAngle - self.angle) < 11:
                return
            if self.angle > h:
                self.playerAngle += 20
            if self.angle < h:
                self.playerAngle -= 20

        def rotate_character(current_angle, new_angle):
            if abs(new_angle - current_angle) > 180:
                if new_angle < current_angle:
                    new_angle += 360
                else:
                    current_angle += 360

            clockwise = new_angle > current_angle
            diff = abs(new_angle - current_angle) % 360
            # print('diff', diff)
            if diff < 10:
                return current_angle
            if clockwise:
                current_angle += 10
            else:
                current_angle -= 10

            current_angle %= 360

            return current_angle

        if self.speed != Vec3(0, 0, 0):
            # interAngle(math.atan2(-self.speed.x, self.speed.y))
            if self.character.isOnGround():
                if self.character.movementState in self.character.actionStates:
                    pass
                else:
                    self.playerM.setH(rotate_character(h, self.angle))

        # anims here
        currentAnim = self.playerM.getCurrentAnim()
        anim = None
        if self.animSeq != None:
            if self.animSeq.isPlaying():
                return

        if self.character.movementState == 'dodging':
            anim = 'dodge'
            self.character.dodgeFrame = self.playerM.getCurrentFrame()
        if self.character.movementState in self.character.airStates:
            if self.character.movementState == 'jumping':
                # if(currentAnim)!="jump":
                anim = 'jump'
            if self.character.movementState == 'falling':
                anim = 'fall'
        if (
            self.character.isOnGround()
            and self.character.movementState != 'dodging'
        ):
            if self.speed != 0:
                anim = 'walk'
            else:
                anim = 'idle'
        if currentAnim != anim:
            self.playerM.setPlayRate(1, anim)
            self.playerM.play(anim)
            # print('anim = ', anim, self.playerM.getCurrentAnim)
        # else:
        #     return
        # else:

    def updateSpirit(self):
        if self.spirit.state == 'float':
            self.spirit.floatUp()
        elif self.spirit.state == 'oscillate':
            self.spirit.oscillate()
        elif self.spirit.state == 'decide':
            self.spirit.decideTarget(self.playerM)
        elif self.spirit.state == 'move':
            self.spirit.takeAction()

    def updateAi(self):
        self.aiWorld.update()
        for vessel in self.vessels:
            vessel.update()

    def collisionSetup(self):
        traverser = CollisionTraverser('collider')
        base.cTrav = traverser
        
        self.collHandEvent = CollisionHandlerEvent()
        self.playerATKNode = self.playerM.attachNewNode(CollisionNode('playeratk'))
        self.playerParrynode = self.playerM.attachNewNode(CollisionNode('playerParry'))

        traverser.addCollider(self.playerATKNode, self.collHandEvent)
        traverser.addCollider(self.playerParrynode, self.collHandEvent)

        
#         self.collHandEvent.addInPattern('%fn-into-%in') 
#         self.collHandEvent.addOutPattern('%fn-out-%(tag)ih')
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
