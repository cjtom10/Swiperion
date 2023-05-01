
#from pandac.PandaModules import loadPrcFileData
#loadPrcFileData('', 'load-display tinydisplay')

#loadPrcFileData('', 'bullet-additional-damping true')
#loadPrcFileData('', 'bullet-additional-damping-linear-factor 0.005')
#loadPrcFileData('', 'bullet-additional-damping-angular-factor 0.01')
#loadPrcFileData('', 'bullet-additional-damping-linear-threshold 0.01')
#loadPrcFileData('', 'bullet-additional-damping-angular-threshold 0.01')
from direct.actor.Actor import Actor
import sys
import direct.directbase.DirectStart

from direct.showbase.DirectObject import DirectObject
from direct.showbase.InputStateGlobal import inputState
from direct.gui.OnscreenText import OnscreenText,TextNode
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.DirectGui import DGG, DirectButton, DirectFrame
from direct.interval.LerpInterval import LerpFunc
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, Wait
from direct.interval.LerpInterval import *
from direct.interval.ActorInterval import ActorInterval, LerpAnimInterval
import logging

import simplepbr
import gltf
from kcc import PandaBulletCharacterController

from panda3d.core import *
from direct.gui.OnscreenText import OnscreenText
from panda3d.bullet import *
from mouseLook import MouseLook
base.disableMouse()
# ml = MouseLook()
# ml.setMouseModeRelative(False)
# ml.setCursorHidden(True)
# ml.centerMouse = True
# ml.mouseLookMode = ml.MLMOrbit
# ml.enable()

class Game(DirectObject):

  def __init__(self):
    base.setBackgroundColor(0.8, 0.7, 0.7, 1)
    base.setFrameRateMeter(True)

    base.cam.setPos(0, -20, 4)
    base.cam.lookAt(0, 0, 0)

    # Light
    alight = AmbientLight('ambientLight')
    alight.setColor(Vec4(0.5, 0.5, 0.5, 1))
    alightNP = render.attachNewNode(alight)

    dlight = DirectionalLight('directionalLight')
    dlight.setDirection(Vec3(1, 1, -1))
    dlight.setColor(Vec4(0.7, 0.7, 0.7, 1))
    dlightNP = render.attachNewNode(dlight)

    simplepbr.init()
    # ml.resolveMouse()
    render.clearLight()
    render.setLight(alightNP)
    render.setLight(dlightNP)
    self.setup()
    # Input
    self.accept('escape', self.doExit)
    self.accept('r', self.doReset)
    self.accept('f1', self.toggleWireframe)
    self.accept('f2', self.toggleTexture)
    self.accept('f3', self.toggleDebug)
    self.accept('f5', self.doScreenshot)
    self.accept('t', self.doSwipe,extraArgs = [self.scanPoints[0]])

    inputState.watchWithModifiers('forward', 'w')
    inputState.watchWithModifiers('left', 'a')
    inputState.watchWithModifiers('reverse', 's')
    inputState.watchWithModifiers('right', 'd')
    inputState.watchWithModifiers('turnLeft', 'q')
    inputState.watchWithModifiers('turnRight', 'e')

    # Task
    taskMgr.add(self.update, 'updateWorld')
    self.swiping = False
    # Physics
    
    self.camPos = self.camTarg.getPos(render)
  def doSwipe(self, swipepoint, entry):
      #puts
      if swipepoint not in self.scanPoints:
          print('u just swiperd')
          return
      self.swiping = True
      self.character.node().setLinearVelocity((0,0,0))
      # h = 
      # p = LerpPosHprInterval(self.playerM, .01, )
      p = LerpPosInterval(self.character, .2,(0,3,1), other=swipepoint )
      a = self.playerM.actorInterval( 'swipe',0,startFrame = 0, endFrame = 40)
      self.credit+=1
      
      def end():
          self.swiping = False
      def cooldown(s):
          self.scanPoints.remove(s)
          # print('removing point')
      def coolup(s):
          self.scanPoints.append(s)
          # print('putting poiont back')
      f = Func(end)
      cd = Func(cooldown, swipepoint)
      cu = Func(coolup, swipepoint)

      seq = Sequence(p,a,f, cd, Wait(5),cu).start()
  # def swipeCooldown(point):
      #temporarilly removes swipepoint
  # _____HANDLER_____


  def doExit(self):
    self.cleanup()
    sys.exit(1)

  def doReset(self):
    self.cleanup()
    self.setup()

  def toggleWireframe(self):
    base.toggleWireframe()

  def toggleTexture(self):
    base.toggleTexture()

  def toggleDebug(self):
    if self.debugNP.isHidden():
      self.debugNP.show()
    else:
      self.debugNP.hide()

  def doScreenshot(self):
    base.screenshot('Bullet')

  # ____TASK___
  def processInput(self, dt):
        
        self.speed = Vec3(0,0,0)
        omega = 0.0
        
        v = 24.0
        vx = .50
        vy = .50
        vz = .5
      
        # if inputState.isSet('run'): 
        #     v = 15.0
        # if self.character.movementState != "attacking":
        
        # if self.character.isAttacking ==False and self.character.isParrying ==False:
        # if self.character.movementState!="attacking":
########KEYBOARD
        # if self.character.movementState == "wallgrab":
        #     self.wallgrabInput()
        #     self.speed = 0
        #     return
        if inputState.isSet('forward'):
            self.speed.setY(v)
        if inputState.isSet('reverse'): 
            self.speed.setY(-v)
        if inputState.isSet('left'):    
            self.speed.setX(-v)
        if inputState.isSet('right'):   
            self.speed.setX(v)
  # def processInput(self, dt, fo):
    # force = Vec3(0, 0, 0)
    # torque = Vec3(0, 0, 0)

    # if inputState.isSet('forward'): force.setY( 1.0)
    # if inputState.isSet('reverse'): force.setY(-1.0)
    # if inputState.isSet('left'):    force.setX(-1.0),torque.setZ( .05)
    # if inputState.isSet('right'):   force.setX( 1.0),torque.setZ(-.05)
    # if inputState.isSet('turnLeft'):  torque.setZ( .5)
    # if inputState.isSet('turnRight'): torque.setZ(-.5)
    
    # #force increases with credit score
    # force *= fo
    # torque *= 2.0

    # force = render.getRelativeVector(self.playerM, force)
    # torque = render.getRelativeVector(self.playerM, torque)

    # self.character.node().setActive(True)
    # self.character.node().applyCentralForce(force)
    # self.character.node().applyTorque(torque)
        self.character.setAngularMovement(omega)
        self.character.setLinearMovement(self.speed, True)

  def doJump(self):
    
    pass
  def update(self, task):
    dt = globalClock.getDt()

    f = self.credit * 2
    if self.swiping==False:
      self.processInput(dt)
    #self.world.doPhysics(dt)
    # self.character.setP(0)
    # self.character.setR(0)
    self.world.doPhysics(dt, 5, 1.0/180.0)

    # self.camdelay(2)
    # self.camTask()
    self.timer-= .016
    self.text.setText(f"Time:{self.timer}\nCredit Score: {self.credit}")
    self.updatePlayer()
    # base.cam.setPos(self.camTarg.getPos())
    
    return task.cont
  def updatePlayer(self):
      self.MP.setPos(self.character.getPos(render))
      self.playerM.setPos(self.character.getPos(render))
      # self.playerM.setH(self.MP, self.charAngle)
      self.playerM.setH(base.cam.getH(render))
      if inputState.isSet('left'):  self.charAngle+=1
      if inputState.isSet('right'): self.charAngle -=1

      ### anims here
      # print('char velocity', self.character.node().getLinearVelocity().z)

      # if abs(self.character.node().getLinearVelocity().y) > .3:
      #     walking = True
      # else:
      #     walking = False
      
      self.anim=self.playerM.getCurrentAnim()


      def animRun(speed):
        self.playerM.setPlayRate( speed,'run')
        if self.anim!='run':
          self.playerM.loop('run')
      def animIdle():
        if self.anim!='idle':
          self.playerM.loop('idle')
      if self.swiping==True:
          return
      # if walking == True:
      #     animRun(1)
      # if walking == False:
      #     animIdle()
      
      # self.playerM
  def camTask(self):
      
      ml.orbitCenter = self.playerM.getPos(render)
      campos = base.camera.getPos(render)
      def moveCam(node):

            node.setPos( self.playerM.getPos(render))
      moveCam(base.camera) 

  def camdelay(self, t):
    
    self.camPos += (self.character.getPos(render) - self.camTarg.getPos(render)) * t
    # self.camTarg.setPos(self.camPos)
    self.camTarg.setPos(self.playerM.getPos(render))
    self.camTarg.setH(self.playerM.getH(render))

    
  def cleanup(self):
    self.world.removeRigidBody(self.groundNP.node())
    self.world.removeRigidBody(self.character.node())
    self.world = None

    self.debugNP = None
    self.groundNP = None
    self.character = None

    self.worldNP.removeNode()

  def setup(self):
    self.worldNP = render.attachNewNode('World')
   
    self.timer = 0
    self.credit = 1
    self.text = TextNode('text')
    self.textNP = aspect2d.attachNewNode(self.text)
    self.textNP.setScale(.08)
    self.textNP.setPos(-.9,0,-.6)
    

    # World
    self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
    self.debugNP.show()
    self.debugNP.node().showWireframe(True)
    self.debugNP.node().showConstraints(True)
    self.debugNP.node().showBoundingBoxes(False)
    self.debugNP.node().showNormals(True)

    #self.debugNP.showTightBounds()
    #self.debugNP.showBounds()
    self.camTarg = self.worldNP.attachNewNode('cam target')
    # base.cam.reparentTo(self.camTarg)
    base.cam.setPos(0,-10,3)

    self.world = BulletWorld()
    self.world.setGravity(Vec3(0, 0, -9.81))
    self.world.setDebugNode(self.debugNP.node())

    # Ground (static)
    shape = BulletPlaneShape(Vec3(0, 0, 1), 1)

    self.groundNP = self.worldNP.attachNewNode(BulletRigidBodyNode('Ground'))
    self.groundNP.node().addShape(shape)
    self.groundNP.setPos(0, 0, -50)
    self.groundNP.setCollideMask(BitMask32.allOn())

    self.world.attachRigidBody(self.groundNP.node())

    self.character =PandaBulletCharacterController(self.world, self.worldNP, 4, 1.5,.5, 1)#,self.charM)

    # player setup
    self.playerM = Actor('char.bam',{ 
                         'idle':'char_IDLE.bam',
                         'run':'char_RUN.bam',
                         'jump':'char_jump.bam',
                         'swipe': 'char_swipe.bam'} )
    self.playerM.reparentTo(self.worldNP)
    self.playerM.setZ(-1)
    self.MP = render.attachNewNode('movementparent')
    shape = BulletSphereShape(1)
    self.charAngle = 0
    # shape = BulletCapsuleShape(1,1.5)

    # self.character = self.worldNP.attachNewNode(BulletRigidBodyNode('Box'))
    # self.character.node().setMass(1.0)
    # self.character.node().addShape(shape)
    # self.character.setPos(0, 0, 5)
    # #self.character.setScale(2, 1, 0.5)
    # self.character.setCollideMask(BitMask32.allOn())
    #self.character.node().setDeactivationEnabled(False)

    # self.world.attachRigidBody(self.character.node())

    visualNP = loader.loadModel('models/box.egg')
    visualNP.clearModelNodes()
    # visualNP.reparentTo(self.character)
    
    #lvl setup
    self.lvl = loader.loadModel('lvl.glb')
    self.lvl.reparentTo(self.worldNP)
    self.geomcount = 6

    self.scanPoints = []
    for x in range(4):
      u = self.lvl.find(f'p{x}')
      self.scanPoints.append(u)


    for i in range(self.geomcount):
                        self.findTris(f'tri{i}',self.lvl)

    self.collisionSetup()

  def make_collision_from_model(self, input_model, node_number, mass, world, target_pos,mask = BitMask32.bit(0),name ='input_model_tri_mesh'):
                # tristrip generation from static models
                # generic tri-strip collision generator begins
                geom_nodes = input_model.find_all_matches('**/+GeomNode')
                geom_nodes = geom_nodes.get_path(node_number).node()
                # print(geom_nodes)
                geom_target = geom_nodes.get_geom(0)
                # print(geom_target)
                output_bullet_mesh = BulletTriangleMesh()
                output_bullet_mesh.add_geom(geom_target)
                tri_shape = BulletTriangleMeshShape(output_bullet_mesh, dynamic=False)
                print(output_bullet_mesh)

                body = BulletRigidBodyNode(name)
                np = render.attach_new_node(body)
                np.node().add_shape(tri_shape)
                np.node().set_mass(mass)
                np.node().set_friction(0.01)
                np.set_pos(target_pos)
                np.set_scale(1)
                # np.set_h(180)
                # np.set_p(180)
                # np.set_r(180)
                # np.set_collide_mask(BitMask32.allOn())
                np.set_collide_mask(mask)
                
                world.attach_rigid_body(np.node())
   
  def findTris(self, name, model):
                shape = model.find(name)
                self.make_collision_from_model(shape,0,0,self.world,shape.getPos())

  def collisionSetup(self):
    traverser = CollisionTraverser('collider')
    base.cTrav = traverser

    self.collHandEvent = CollisionHandlerEvent()
    self.collHandEvent.addInPattern('%fn-into-%in') 

    self.charTrigger=self.playerM.attachNewNode(CollisionNode('player'))
    sphere =CollisionSphere(0,0,0, 1.5)
    self.charTrigger.node().addSolid(sphere)
    self.charTrigger.show()
    traverser.addCollider(self.charTrigger, self.collHandEvent)

    self.scanPoints = []
    for x in range(4):
      u = self.lvl.find(f'p{x}')
      self.scanPoints.append(u)
      collider = u.attachNewNode(CollisionNode(f'sensor{x}'))
      collider.node().addSolid(sphere)
      collider.show()

      traverser.addCollider(collider, self.collHandEvent)


    # self.findoppa=self.playerNP.attachNewNode(CollisionNode('sensor'))
    # sphere =CollisionSphere(0,1,0, 1)
    # self.findoppa.node().addSolid(sphere)

    # self.collHandEvent = CollisionHandlerEvent()
    # self.collHandEvent.addInPattern('%fn-into-%in') 
    # traverser.addCollider(self.findoppa, self.collHandEvent)

    # traverser.addCollider(self.found, self.collHandEvent)

    for i in range(len(self.scanPoints)):
      self.accept(f'player-into-sensor{i}',self.doSwipe, extraArgs = [self.scanPoints[i]] )

    #scanner hitboxes
    # for i in range(len(self.scanPoints)):

        

    # Bullet nodes should survive a flatten operation!
    #self.worldNP.flattenStrong()
    #render.ls()

game = Game()
run()

