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
from direct.filter.CommonFilters import CommonFilters
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
import gltf

from kcc import PandaBulletCharacterController


class Game(DirectObject):
    def __init__(self):

        # now, x and y can be considered relative movements

        self.shader = Shader.load(Shader.SL_GLSL, "sders/vert.vert", "sders/frag.frag")
        pipeline = simplepbr.init()
        pipeline.use_normal_maps = True
        pipeline.use_occlusion_maps = True
        gltf.patch_loader(loader)

        base.setBackgroundColor(0, 0.1, 0, 1)
        base.setFrameRateMeter(True)

        


        
        # scene_filters = CommonFilters(base.win, base.cam)
        # scene_filters.set_bloom()
        # scene_filters.set_high_dynamic_range()
        # scene_filters.set_exposure_adjust(1.1)
        # scene_filters.set_gamma_adjust(1.1)



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
        self.storage = NodePath('storage') #non visible storage node
        self.setup()

        render.clearLight()
        ##----lights
        sun = DirectionalLight("sun")
        sun.set_color_temperature(10000)
        sun.color = sun.color * 2
        self.sun_path = render.attach_new_node(sun)
        self.sun_path.set_pos(500, 0, 5)
        self.sun_path.look_at(0, 0, 0)
        self.worldNP.setLight(self.sun_path)
        # self.sun_path.hprInterval(10.0, (self.sun_path.get_h(), self.sun_path.get_p() - 360, self.sun_path.get_r()), bakeInStart=True).loop()

        sun.get_lens().set_near_far(1, 30)
        sun.get_lens().set_film_size(20, 40)
        sun.show_frustum()
        sun.set_shadow_caster(True, 4096, 4096)

        alight = AmbientLight("sky")
                # alight.set_color(VBase4(skycol * 0.04, 1))
        alight.set_color((.5,0.4,0.6,1))
        alight_path = render.attach_new_node(alight)
        # self.worldNP.set_light(alight_path)

        plight_1 = PointLight('plight')
        # add plight props here
        plight_1_node = render.attach_new_node(plight_1)
        # group the lights close to each other to create a sun effect
        plight_1_node.set_pos(random.uniform(-21, -20), random.uniform(-21, -20), random.uniform(20, 21))
        render.set_light(plight_1_node)

        self.worldNP.setAttrib(LightRampAttrib.makeSingleThreshold(0, 0.5))

        # render.setShader(self.shader)
       

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

        # self.animSeq = Sequence()

    def doCrouch(self):
        self.character.startCrouch()

    def doAttack(self ):
        print('attack no', self.currentStrike)
        if self.character.movementState in self.character.airStates: #or self.character.isOnGround()==False:
            return
        
        # if self.currentStrike>=3:
        #     self.currentStrike =  1
        #     print('combo limit')
        # return
        # if self.character.movementState == 'attacking':
        if self.isPraying==True:
            print(';cant attaklc, praying')
            return
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

        # if self.speed != Vec3(0, 0, 0):
        #     self.playerM.setH(self.angle )
        h=self.playerM.getH()
        if self.speed!=(0,0,0):
                h=self.angle
        
        print('attacl no', self.currentStrike)
        # self.character.atkDir = self.playerM.getQuat().getForward() maybe set this during active frames

        # self.speed = 0
        self.isAttacking = True
        self.character.movementState = 'attacking'
        if self.currentStrike == 1:
            self.atkAnim('strike1', 4, 20,30,self.playerATKNode, self.handL, CollisionSphere(0,0,0,.5),h)
            self.currentStrike += 1
            return
        if self.currentStrike == 2:
            self.atkAnim('strike2', 4, 20,30,self.playerATKNode, self.handR, CollisionSphere(0,0,0,.5),h)
            self.currentStrike += 1
            return
        if self.currentStrike == 3:
            self.atkAnim('strike3', 4, 20,30,self.playerATKNode, self.handR, CollisionSphere(0,0,0,.5),h)
            self.currentStrike += 1
            #     return
        # if self.currentStrike==2:

    def doPrayer(self):
        if self.isPraying == True:
            print('already praying')

            return

        if self.character.movementState == 'attacking':
            if self.animSeq != None:
                self.animSeq.pause()
                self.animSeq = None
                self.finishAction()
        # if self.character.movementState == 'attacking':
        #     if self.animSeq != None:
        #         self.animSeq.pause()
        #         self.animSeq = None
        if self.speed != Vec3(0, 0, 0):
            self.playerM.setH(self.angle)
        h=self.playerM.getH()
        self.isPraying = True
        self.character.movementState = 'attacking'
        self.character.atkDir = 0
        no = random.randint(1, 2)
        self.atkAnim(
            f'prayer{no}',
            4,
            16,
            20,
            self.playerParrynode,
            self.playerM,
            CollisionSphere(0,0,3,2),
            h,
            prayer = True
        )

    def check4Queue(self):
        """if there is a queued attack, this will trigger it"""
        if self.character.movementState != 'attacking':
            self.character.movementState = 'attacking'
        if (
            self.attackQueued == True
        ):   # or self.character.movementState == 'dodging':

            # self.finish()
            # if type == 'slash':
            if self.speed!=(0,0,0):
                h=self.angle
            else:
                h=self.playerM.getH()
            if self.currentStrike == 2:
                self.atkAnim('strike2', 4, 20,30, self.playerATKNode, self.handR, CollisionSphere(0,0,0,.5),h)
                self.isAttacking = True
                self.currentStrike += 1
                self.attackQueued = False
                return
            if self.currentStrike == 3:
                self.atkAnim('strike3', 4, 20,30,self.playerATKNode, self.handR, CollisionSphere(0,0,0,.5),h)
                self.isAttacking = True
                self.currentStrike += 1
                self.attackQueued = False
        else:
            return

    # def atkAnim(self,order,)
    def atkAnim(self, anim, activeFrame, bufferStart,bufferEnd, node, bone, shape, targetH, prayer = False):

        if self.animSeq is not None:  # end attack anim sequence
            if self.animSeq.isPlaying():
                self.animSeq.pause()
        
            

        def atkFalse():
            self.isAttacking = False
            self.isPraying = False
        a1 = self.playerM.actorInterval(
            anim, startFrame=0, endFrame=activeFrame
        )
        active = self.playerM.actorInterval(
            anim, startFrame=activeFrame + 1, endFrame=bufferStart
        )
        buffer = self.playerM.actorInterval(
            anim, startFrame=bufferStart + 1, endFrame=bufferEnd
        )


        setH = LerpHprInterval(self.playerM, .1, (targetH,0,0))
        atkF = Func(atkFalse)
        fin = Func(self.finishAction)
        c4q = Func(self.check4Queue)

        hB = Func(self.attachHB, bone, node, shape)
        noHB = Func(self.detachHB, node)

        if prayer == True:
            def makeVis():
                self.prayerFX.reparentTo(self.playerM) 
            rp = Func(makeVis)
            visual = Sequence( rp,
                               LerpTexOffsetInterval(self.prayerFX, 1,(1,0),(0,0), textureStage=self.ts0))
            prayer = Sequence(
                                    Parallel(a1,setH),
                                    hB,
                                    active, 
                                    noHB, ### MAYBE move atkf to end so ppl dont spam prayer
                                    c4q, 
                                    buffer,atkF,
                                    fin)
            self.animSeq =Parallel(visual,prayer)
        else:

            self.animSeq = Sequence(Parallel(a1,setH),
                                    hB,
                                    active, 
                                    Parallel(atkF,noHB), 
                                    c4q, 
                                    buffer, 
                                    fin)
        
        #fx for prayer
        
            

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
        # self.footR = self.playerM.expose_joint(None, 'modelRoot', 'foot.R')
        # self.footL = self.playerM.expose_joint(None, 'modelRoot', 'foot.L')
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
        self.isPraying=False
        self.isAttacking=False
        self.character.movementState = 'endaction'
        self.prayerFX.reparentTo(self.storage)
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
                and self.isPraying == False
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


        # print('is attacking?', self.isAttacking, 'isp[raying]?', self.isPraying)

        oldCharPos = self.character.getPos(render)
        self.character.setH(base.camera.getH(render))
        self.character.update()   # WIP
        newCharPos = self.character.getPos(render)
        delta = newCharPos - oldCharPos

        self.world.doPhysics(dt, 4, 1.0 / 120.0)

        
 #######update cam 
        self.camdummy.setPos(base.cam.getPos(render))
        char2cam = self.character.getPos(self.camdummy)
        

        c = float(( char2cam-Vec3(0,0,0)).length())
        a = float(char2cam.z)
        b = float(char2cam.y)
        # camPitch = math.atan(a/b) * 180 / math.pi

        camPitch = math.degrees(math.asin(a/c))
        ypos= base.camera.getY()
        xpos= base.camera.getX()
        # if self.character.isOnGround() ==False:
        base.cam.setP(camPitch)
        # print(a,)
        # print('campitch',camPitch,'char2cam', char2cam)
        # print('char dist to cam:', a,b,c)

        # base.camera.setY(self.character.getY())

        if char2cam.y<9 or char2cam.y> 12:
            ypos += delta.y
        if char2cam.x<-4 or char2cam.x> 4:
            xpos += delta.x
        # if char2cam>8:
        #     ypos += delta.y
        base.camera.setX(xpos)
        base.camera.setY(ypos)
        # base.cam.setP(camPitch)
        # print('campit h',camPitch,'abc',a,b,c)
      
        self.updatePlayer()
        if self.character.movementState != 'attacking':
            self.currentStrike = 1
            # print('state attacking', self.isAttacking, self.currentStrike)
        # update enemy aijohn
        self.updateAi()
        self.updateSpirit()

        return task.cont

    def cleanup(self):
        self.world = None
        self.worldNP.removeNode()

    def setup(self):
        self.worldNP = render.attachNewNode('World')

        self.playerHP = 100

        # World
        self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
        self.debugNP.show()

        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))
        self.world.setDebugNode(self.debugNP.node())

        #camera
        self.camdummy = NodePath('camdummy')
        base.cam.setPos(0, -7,5)
        base.cam.setP(-7)

        #hud TODO - make health an icon that changes from green to red
        self.hud = TextNode('node name')
        self.hud.setText(f"HP{self.playerHP}")
        self.hudNP = aspect2d.attachNewNode(self.hud)
        self.hudNP.setScale(0.07)
        self.hudNP.setPos(-1.5,0,-.8)
        

########## lvl]



        #ground
        shape = BulletPlaneShape(Vec3(0, 0, 1.0), 0)

        np = self.worldNP.attachNewNode(BulletRigidBodyNode('Ground'))
        np.node().addShape(shape)
        np.setPos(0, 0, 0)
        np.setCollideMask(BitMask32.allOn())

        self.lvlSetup()


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

######## player setup
        self.character = PandaBulletCharacterController(
            self.world, self.worldNP, 1.75, 1.3, 0.5, 2
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

        #fx for prayer

        self.ts0 = TextureStage('texstage0')
        self.ts0.setTexcoordName("0")
        self.ts0.setMode(TextureStage.MReplace)
        self.ts0.setSort(0)

        brushtex = loader.loadTexture('models/player/watercolorstrike.png')
        self.prayerFX = loader.loadModel('models/player/prayerfx.glb')
        self.prayerFX.clearTexture()
        self.prayerFX.reparentTo(self.storage)

        fxmat = Material("material")
        fxmat.setEmission((1,1,1,1))
        fxmat.setSpecular((1,1,1,0))

        self.prayerFX.setMaterial(fxmat)
        self.prayerFX.clearTexture()
        self.prayerFX.setTransparency(True)
        self.prayerFX.setTexture(self.ts0, brushtex,1)
        self.prayerFX.setShader(self.shader)

        

        self.playerATKNode = self.playerM.attachNewNode(CollisionNode('playeratk'))
        self.playerParrynode = self.playerM.attachNewNode(CollisionNode('playerparry'))

        self.handR = self.playerM.expose_joint(None, 'modelRoot', 'Hand.R')
        self.handL = self.playerM.expose_joint(None, 'modelRoot', 'Hand.L')

        self.playerM.setScale(.5)
        self.playerM.reparentTo(self.character.movementParent)
        self.playerIdle = True

        self.atx = None
        self.isAttacking = False   # when this is false, dodges, movement, jumps end attack, asttacking
        self.isPraying = False
        self.angle = 0
        self.playerAngle = 0
        self.animSeq = None
        self.currentStrike = 1
        self.playerSA = 0 #poise value, increases with each attack

        self.playerHBSetup()

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
        self.collisionSetup()


    def playerHBSetup(self, HBvisible = True):

        self.playerHB = []
        self.isHit = False
          
       #positions for collision soluids
        self.head = self.playerM.expose_joint(None, 'modelRoot', 'head')
        self.chest = self.playerM.expose_joint(None, 'modelRoot', 'chest')
        rightbicep= self.playerM.expose_joint(None, 'modelRoot', 'bicep.R')
        # self.rightfoot = self.playerM.expose_joint(None, 'modelRoot', 'foot.R')
        # self.leftfoot = self.playerM.expose_joint(None, 'modelRoot', 'foot.L')
        rightforearm= self.playerM.expose_joint(None, 'modelRoot', 'forarm.R')
        rightthigh = self.playerM.expose_joint(None, 'modelRoot', 'femur.R')
        rightshin = self.playerM.expose_joint(None, 'modelRoot', 'shin.R')
        leftbicep= self.playerM.expose_joint(None, 'modelRoot', 'bicep.L')
        leftforearm= self.playerM.expose_joint(None, 'modelRoot', 'forarm.L')
        leftthigh = self.playerM.expose_joint(None, 'modelRoot', 'femur.L')
        leftshin = self.playerM.expose_joint(None, 'modelRoot', 'shin.L')

        # collision solides
        headHB = CollisionSphere(0,0,0, .1)
        chestHB= CollisionSphere(0,.2,0,.4)
        arm =  CollisionCapsule((0,-.2,0),(0,.8,0),0.07)
        leg =  CollisionCapsule((0,-.38,0),(0,1,0),0.1)   

        
        #attach the solidss
        self.headHB = self.head.attachNewNode(CollisionNode('playerhead'))
        self.headHB.node().addSolid(headHB)
        self.headHB.setZ(-.2)
        # self.headHB.show()
        self.playerHB.append(self.headHB)
    
        self.chestHB = self.chest.attachNewNode(CollisionNode('playerchest'))
        self.chestHB.node().addSolid(chestHB)
        self.chestHB.setY(-.2)
        # self.chestHB.show()
        self.playerHB.append(self.chestHB)
        # self.chestHB.reparentTo(self.characterHB)
    
        self.bicepR = rightbicep.attachNewNode(CollisionNode('playerbicepr'))
        self.bicepR.node().addSolid(arm)
        # self.bicepR.show()
        self.playerHB.append(self.bicepR)
    
        self.forarmR = rightforearm.attachNewNode(CollisionNode('playerforearmr'))
        self.forarmR.node().addSolid(arm)
        # self.forarmR.show()
        self.playerHB.append(self.forarmR)
    
        self.thighR = rightthigh.attachNewNode(CollisionNode('playerthighr'))
        self.thighR.node().addSolid(leg)
        # self.thighR.show()
        self.playerHB.append(self.thighR)
        
        self.shinR = rightshin.attachNewNode(CollisionNode('playershinr'))
        self.shinR.node().addSolid(leg)
        # self.shinR.show()
        self.playerHB.append(self.shinR)
    
        self.bicepL = leftbicep.attachNewNode(CollisionNode('playerbicepl'))
        self.bicepL.node().addSolid(arm)
        # self.bicepL.show()
        self.playerHB.append(self.bicepL)
    
        self.forarmL = leftforearm.attachNewNode(CollisionNode('playerforearml'))
        self.forarmL.node().addSolid(arm)
        # self.forarmL.show()
        self.playerHB.append(self.forarmL)
    
        self.thighL = leftthigh.attachNewNode(CollisionNode('playerthighl'))
        self.thighL.node().addSolid(leg)
        # self.thighL.show()
        self.playerHB.append(self.thighL)
        
        self.shinL = leftshin.attachNewNode(CollisionNode('playershinl'))
        self.shinL.node().addSolid(leg)
        # self.shinL.show()
        self.playerHB.append(self.shinL)
    
        if HBvisible ==True:
            for node in self.playerHB:
                node.show()        
    
#         self.collHandEvent.addInPattern('%fn-into-%in') 
#         self.collHandEvent.addOutPattern('%fn-out-%(tag)ih')
    def lvlSetup(self):
        self.lvl = loader.loadModel('models/lvlunit01.glb')
        self.lvl.reparentTo(render)
        self.make_collision_from_model(self.lvl, 0,0,self.world,Point3(0,0,0))

    def make_collision_from_model(self, input_model, node_number, mass, world, target_pos, ):
        # tristrip generation from static models
        # generic tri-strip collision generator begins
        # return
        geom_nodes = input_model.find_all_matches('**/+GeomNode')
        geom_nodes = geom_nodes.get_path(node_number).node()
        # print(geom_nodes)
        geom_target = geom_nodes.get_geom(0)
        # print(geom_target)
        output_bullet_mesh = BulletTriangleMesh()
        output_bullet_mesh.add_geom(geom_target)
        tri_shape = BulletTriangleMeshShape(output_bullet_mesh, dynamic=False)
        print(output_bullet_mesh)

        body = BulletRigidBodyNode('input_model_tri_mesh')
        np = render.attach_new_node(body)
        np.node().add_shape(tri_shape)
        np.node().set_mass(mass)
        np.node().set_friction(0.01)
        np.set_pos(target_pos)
        np.set_scale(1)
  
    #     np.set_collide_mask(BitMask32.allOn())
        np.set_collide_mask(BitMask32.bit(1))
        world.attach_rigid_body(np.node())


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

    #####safety nets:    #
        if self.character.isOnGround() and self.character.movePoints!=3:
            self.character.movePoints=3
        if self.character.movementState!='attacking':
            if (self.isPraying==False 
            and self.isAttacking==False):
                # if self.attached == True:
                    self.detachHB(self.playerATKNode)
                    self.detachHB(self.playerParrynode)

        # 3playerpoise
        self.playerSA = self.currentStrike
        # print('player superarmor, ', self.playerSA)

        # set angle here
        self.angle = (
            math.degrees(math.atan2(-self.speed.x, self.speed.y))
        ) % 360
        # self.angle = self.angle % 360
        h = self.playerM.getH() % 360



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



    def checkGhost(self, task):
        pass


    ###### Collision events here
    def collisionSetup(self):
        traverser = CollisionTraverser('collider')
        base.cTrav = traverser
        
        
        self.collHandEvent = CollisionHandlerEvent()
        self.collHandEvent.addInPattern('%fn-into-%in')     

        traverser.addCollider(self.playerATKNode, self.collHandEvent)
        traverser.addCollider(self.playerParrynode, self.collHandEvent)

        for vessel in self.vessels:
            traverser.addCollider(vessel.lclaw_hitbox,self.collHandEvent)
            traverser.addCollider(vessel.rclaw_hitbox,self.collHandEvent)

    #     self.collisionEvents()
    # def collisionEvents(self):

        # print('svessels',self.vessels[0].)
        #possessed hits p[layer]     
        print(self.playerHB)  
        for bodypart in self.playerHB: 
            
                # self.accept()
            for enemy in self.vessels:
                self.accept(f'{enemy.name}clawL-into-{bodypart.name}', self.takeHit, extraArgs=[enemy])
                self.accept(f'{enemy.name}clawR-into-{bodypart.name}', self.takeHit, extraArgs=[enemy])
                # self.accept(f'{enemy.NP.name}attack-out-pdodgecheck', self.pdodge,  extraArgs=[False])
                self.accept(f'{enemy.name}clawL-into-playerparry', self.parryEnemy, extraArgs=[enemy])
                self.accept(f'{enemy.name}clawR-into-playerparry', self.parryEnemy, extraArgs=[enemy])
        
        #player hits possessed
        for vessel in self.vessels:
            #  self.accept(f'playeratk-into-{vessel.name}hitbox', self.hitEnemy, extraArgs=[enemy])
            for bodyPart in vessel.HB:
                self.accept(f'playeratk-into-{bodyPart.name}', self.hitEnemy, extraArgs=[enemy])
       
        #player parries possessed

        #player parries spirit
    def hitCheck(self, who, v):
        who.isHit=v
    def takeHit(self,enemy, entry):
        
        if self.isHit  == True:
            return
        self.isHit = True
        print(enemy.name, 'hits player', entry)
        # if player ss> enemysa, wait .5 sec, self.ishit = False
        #else, play take hit anim, ishit = False
        if enemy.SA < self.playerSA:
            print('player is hit butdoes not stagger')
            
        if enemy.SA > self.playerSA:
            print('player is hit and staggers')
        #do sequence, ishit is false at the end
    def hitEnemy(self, enemy, entry):
        #if possesed m= flase return
        if enemy.isHit==True:
            return
        enemy.isHit = True
        # print('player hits', enemy.name, entry)
        p=None
        r=None
        def end():
            self.hitcontact=False
            enemy.isHit =False
            enemy.state = 'pursue'#maybe add a buffer state
        if self.animSeq!=None:
            p = Func(self.animSeq.pause)#### player hitstopping
            r = Func(self.animSeq.resume)
        if self.animSeq==None:
            def noseq():
                pass
            p = Func(noseq)
            r = Func(noseq)
        e =Func(end)
        if enemy.SA >= self.playerSA:
            print('enemy is hit butdoes not stagger')
            def twitch(p):
           
                torso=enemy.model.controlJoint(None, "modelRoot", "torso")
                torso.setP(p)
            
               #stop = Func(enemy.model.stop())#enemy anim stop
            a = Func(twitch, 30)
            b = Func(twitch, 0)
            
            hitseq =Sequence(a, p, Wait(.1),b, r,e)

        if enemy.SA < self.playerSA:
            print('enemy is hit and staggers')
            hitStop = Sequence(p, Wait(.1), r)
            anim = enemy.possessed_model.actorInterval('stagger')
            hitseq =Sequence(Parallel(hitStop, anim),e)
        #do sequence, ishit is false at the end


        hitseq.start()
            # if enemy.health<=0:
            #     self.enemydeath(enemy)
    
    def parryEnemy(self, enemy, entry):
       
        if self.isHit  == True:
            return
        self.isHit = True
        print('player deflects', enemy.name)

    def parrySpirit(self, spirit,entry):
        print('parried spirtitr')
        # ghost = self.ghost.node()
        # for node in ghost.getOverlappingNodes():
        #     print ("Ghost collides with", node)
        # return task.cont

    def spiritPossesses(self,entry,spirit,vessel):
        pass
    
    # def updatePlayer(self):

    #     else:

    #         self.playerIdle = True


game = Game()
run()
