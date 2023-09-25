
from pandac.PandaModules import loadPrcFileData
loadPrcFileData("", "sync-video t")

#from pandac.PandaModules import loadPrcFileData
#loadPrcFileData('', 'load-display tinydisplay')

import sys
import time
import direct.directbase.DirectStart

from direct.actor.Actor import Actor
from direct.interval.LerpInterval import LerpPosInterval
from direct.showbase.DirectObject import DirectObject
from direct.showbase.InputStateGlobal import inputState

from panda3d.core import *
from panda3d.core import NodePath

from panda3d.bullet import *

from direct.gui.OnscreenText import OnscreenText
from direct.interval.LerpInterval import LerpPosInterval
from direct.interval.IntervalGlobal import *


import gltf
import simplepbr

import math

class Game(DirectObject):

  def __init__(self):
    base.setBackgroundColor(0.1, 0.1, 0.8, 1)
    base.setFrameRateMeter(True)

    # base.cam.setPos(0, -20, 4)
    base.cam.lookAt(0, 0, 0)

    pipeline = simplepbr.init()
    pipeline.use_normal_maps = True
    pipeline.use_occlusion_maps = True
    # gltf.patch_loader(loader)

    # Light
    alight = AmbientLight('ambientLight')
    alight.setColor(Vec4(0.5, 0.5, 0.5, 1))
    alightNP = render.attachNewNode(alight)

    dlight = DirectionalLight('directionalLight')
    dlight.setDirection(Vec3(1, 1, -1))
    dlight.setColor(Vec4(0.7, 0.7, 0.7, 1))
    dlightNP = render.attachNewNode(dlight)

    render.clearLight()
    render.setLight(alightNP)
    render.setLight(dlightNP)

    # Input
    self.accept('escape', self.doExit)
    self.accept('r', self.doReset)
    self.accept('f1', self.toggleWireframe)
    self.accept('f2', self.toggleTexture)
    self.accept('f3', self.toggleDebug)
    self.accept('f5', self.doScreenshot)

    #self.accept('space', self.doJump)
    #self.accept('c', self.doCrouch)

    # inputState.watchWithModifiers('forward', 'w')
    # inputState.watchWithModifiers('left', 'a')
    # inputState.watchWithModifiers('reverse', 's')
    # inputState.watchWithModifiers('right', 'd')
    # inputState.watchWithModifiers('turnLeft', 'q')
    # inputState.watchWithModifiers('turnRight', 'e')
    

    # Task
    taskMgr.add(self.update, 'updateWorld')

    # Physics
    self.setup()

    self.accept('w',self.spaceCheck, [self.player, 'forward'])
    self.accept('s',self.spaceCheck, [self.player, 'back'])
    self.accept('a',self.spaceCheck, [self.player, 'left'])
    self.accept('d',self.spaceCheck, [self.player, 'right'])
    #for testing purposes - n
    self.accept('space',self.move, [self.player])

    self.camNode = self.worldNP.attachNewNode('camnode')
    base.cam.reparentTo(self.camNode)
    base.cam.setPos(-2,-12,3)
    base.cam.setP(-10)


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

  #def doJump(self):
  #  self.player.setMaxJumpHeight(5.0)
  #  self.player.setJumpSpeed(8.0)
  #  self.player.doJump()

  #def doCrouch(self):
  #  self.crouching = not self.crouching
  #  sz = self.crouching and 0.6 or 1.0

  #  self.player.NP2.setScale(Vec3(1, 1, sz))

  
  # ____TASK___

  def spaceCheck(self,char, direction):
        
        if char.is_Moving:
           return
        
        marker_x, marker_y = self.marker_x, self.marker_y
        if direction == 'forward':
            marker_y += 1
        elif direction == 'back':
            marker_y -= 1
        elif direction == 'left':
            marker_x -= 1
        elif direction == 'right':
            marker_x += 1

        # cancel if out of bounds
        if marker_x < max(0, char.X_Pos - 1) or marker_x > min(len(self.level), char.X_Pos + 1):
            return
        if marker_y < max(0, char.Y_Pos - 1) or marker_y > min(len(self.level[0]), char.Y_Pos + 1):
            return
        self.marker_x, self.marker_y = marker_x, marker_y

        self.moveMarker.reparentTo(render)
        marker_move = LerpPosInterval(self.moveMarker, 0.1, self.level[self.marker_x][self.marker_y].getPos())
        marker_move.start()

        

  def move(self, char):
     if char.is_Moving:
           return
     
     char.X_Pos, char.Y_Pos = self.marker_x, self.marker_y
     char.target_Pos = self.moveMarker.getPos()

     self.moveMarker.reparentTo(self.storage)
    
  def processInput(self, dt):
    speed = Vec3(0, 0, 0)
    omega = 0.0

    # if inputState.isSet('forward'): speed.setY( 2.0)
    # if inputState.isSet('reverse'): speed.setY(-2.0)
    # if inputState.isSet('left'):    speed.setX(-2.0)
    # if inputState.isSet('right'):   speed.setX( 2.0)
    # if inputState.isSet('turnLeft'):  omega =  120.0
    # if inputState.isSet('turnRight'): omega = -120.0

    self.player.setAngularMovement(omega)
    self.player.setLinearMovement(speed, True)

  def update(self, task):
    dt = globalClock.getDt()

    # self.processInput(dt)
    self.world.doPhysics(dt, 4, 1./240.)

    self.camNode.setPos(self.player.NP.getPos(render))

    self.ap.setText(f'AP:{self.player.AP}')
    self.player.update_Character(dt)

    return task.cont

  def cleanup(self):
    self.world = None
    self.worldNP.removeNode()

  def lvl(self, count = 100):
    block = loader.loadModel('block.glb')
    block.reparentTo(self.worldNP)

    size = 20
    spacing = 2
    nodeCount = count

    self.level = []


      
      # tile.setX(i+1)
    for x in range(0, size, spacing):
          self.level.append([])
          for y in range(0, size, spacing):
             
              tile = self.worldNP.attachNewNode(f'tile_{x}_{y}')
              
              tile.setPos(x,y,0)
              self.level[-1].append(tile)
              block.instanceTo(tile)
              if nodeCount > 0:
                  nodeCount -= 1
         
    # print(self.level)        
    # for t in range(len(self.level)):
    #   block.instanceTo(self.level[t])             
                  # print(tile.getPos())

    # print(self.level)

  def setup(self):
    self.worldNP = render.attachNewNode('World')

    # World
    self.debugNP = self.worldNP.attachNewNode(BulletDebugNode('Debug'))
    self.debugNP.show()

    self.world = BulletWorld()
    self.world.setGravity(Vec3(0, 0, -9.81))
    self.world.setDebugNode(self.debugNP.node())

    self.storage = NodePath('storage')

    # Ground
    shape = BulletPlaneShape(Vec3(0, 0, 1), 0)

    #img = PNMImage(Filename('models/elevation2.png'))
    #shape = BulletHeightfieldShape(img, 1.0, ZUp)

    np = self.worldNP.attachNewNode(BulletRigidBodyNode('Ground'))
    np.node().addShape(shape)
    np.setPos(0, 0, 0)
    np.setCollideMask(BitMask32.allOn())

    self.world.attachRigidBody(np.node())

    # Box
    shape = BulletBoxShape(Vec3(1.0, 3.0, 0.3))

    np = self.worldNP.attachNewNode(BulletRigidBodyNode('Box'))
    np.node().setMass(50.0)
    np.node().addShape(shape)
    np.setPos(3, 0, 4)
    np.setH(0)
    np.setCollideMask(BitMask32.allOn())

    self.world.attachRigidBody(np.node())

    self.lvl()


    self.player = Character(self.worldNP,
                            self.world,
                            loader.loadModel('guy_static.glb'),
                            self.level[0][0].getPos()
                            )
    self.moveMarker = loader.loadModel('move_marker.glb')
    self.moveMarker.setScale(.9)
    self.moveMarker.reparentTo(self.storage)
    self.moveMarker.setTransparency(True)
    self.marker_x = 0
    self.marker_y = 0
    
    # self.characterSetup(loader.loadModel('guy_static.glb'),
    #                      self.level[0][0].getPos())
    # self.player.characterSetup(loader.loadModel('guy_static.glb'),
    #                      0, 0)

    #display AP
    self.ap = OnscreenText(text = f'AP:{self.player.AP}')
    self.ap.setPos(-1,-.8)
  
  # def characterSetup(self, model, startpoint):
  #   # Character
  #   h = 1.75
  #   w = 0.4
  #   shape = BulletCapsuleShape(w, h - 2 * w, ZUp)

  #   self.player = BulletCharacterControllerNode(shape, 0.4, 'Player')
    
  #   # self.player.setMass(20.0)
  #   # self.player.setMaxSlope(45.0)
  #   # self.player.setGravity(9.81)
  #   self.player.NP = self.worldNP.attachNewNode(self.player)

  #   model.reparentTo(self.player.NP)
  #   model.setZ(-1)
  #   self.player.NP.setPos(-2, 0, 10)
  #   # self.player.NP.setH(-90)
  #   self.player.NP.setCollideMask(BitMask32.allOn())
  #   self.world.attachCharacter(self.player)

  #   self.player.NP.setPos(startpoint)




class Character():
  def __init__(
      self,
      worldNP: NodePath,
      world: BulletWorld,
      model,
      startpoint
      ):
    self.AP = 0
    self.world = world
    self.worldNP = worldNP
    self.model = model
    self.startPoint = startpoint

    self.X_Pos = int(self.startPoint.x)
    self.Y_Pos = int(self.startPoint.y)
    self.current_Pos = Point3(self.X_Pos, self.Y_Pos, 0)
    self.target_Pos = Point3(self.X_Pos, self.Y_Pos, 0)
    self.is_Moving = False

  # def characterSetup(self, model, startpoint):
    # Character
    h = 1.75
    w = 0.4
    shape = BulletCapsuleShape(w, h - 2 * w, ZUp)

    # self.controller = BulletCharacterControllerNode(shape, 0.4, 'Player')
    
    # self.player.setMass(20.0)
    # self.player.setMaxSlope(45.0)
    # self.player.setGravity(9.81)
    self.NP = self.worldNP.attachNewNode('playerNode')

    model.reparentTo(self.NP)

    # model.setZ(-1)
    # self.NP.setPos(-2, 0, 10)
    # self.player.NP.setH(-90)
    # self.NP.setCollideMask(BitMask32.allOn())
    # self.world.attachCharacter(self.controller)

    self.NP.setPos(self.startPoint)

  def update_Character(self,d):
     
    # self.current_Pos = Point3(self.X_Pos, self.Y_Pos, 0)
    #  self.NP.setPos(self.current_Pos)
    self.current_Pos = self.NP.getPos(render)
     #moving
    if (self.current_Pos - self.target_Pos).length() > 0.1:
        self.is_Moving = True
        #lerp between points
        marker_move = LerpPosInterval(self.NP, 0.1, self.target_Pos)
        marker_move.start()
    else:
        self.is_Moving = False
        

game = Game()
run()


