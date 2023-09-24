
from pandac.PandaModules import loadPrcFileData
loadPrcFileData("", "sync-video t")

#from pandac.PandaModules import loadPrcFileData
#loadPrcFileData('', 'load-display tinydisplay')

import sys
import time
import direct.directbase.DirectStart

from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject
from direct.showbase.InputStateGlobal import inputState

from panda3d.core import *
from panda3d.core import NodePath

from panda3d.bullet import *

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
    gltf.patch_loader(loader)

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
    

    self.accept('w',self.move, [self.playerNP, 'forward'])
    self.accept('s',self.move, [self.playerNP, 'back'])
    self.accept('a',self.move, [self.playerNP, 'left'])
    self.accept('d',self.move, [self.playerNP, 'right'])

    self.camNode = self.worldNP.attachNewNode('camnode')
    base.cam.reparentTo(self.camNode)
    base.cam.setPos(0,-10,7)
    base.cam.setP(-30)


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

  #  self.playerNP2.setScale(Vec3(1, 1, sz))

  
  # ____TASK___

  def move(self, char, direction):
        if direction == 'forward' and self.player_y < len(self.level[0]) - 1:
            self.player_y += 1
        elif direction == 'back' and self.player_y > 0:
            self.player_y -= 1
        elif direction == 'left' and self.player_x > 0:
            self.player_x -= 1
        elif direction == 'right' and self.player_x < len(self.level) - 1:
            self.player_x += 1
        self.playerNP.setPos(self.level[self.player_x][self.player_y].getPos())
    
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

    self.processInput(dt)
    self.world.doPhysics(dt, 4, 1./240.)

    self.camNode.setPos(self.playerNP.getPos(render))

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

    self.characterSetup(loader.loadModel('guy_static.glb'),
                         0, 0)

  
  def characterSetup(self, model, grid_x, grid_y):
    # Character
    h = 1.75
    w = 0.4
    shape = BulletCapsuleShape(w, h - 2 * w, ZUp)

    self.player = BulletCharacterControllerNode(shape, 0.4, 'Player')
    
    # self.player.setMass(20.0)
    # self.player.setMaxSlope(45.0)
    # self.player.setGravity(9.81)
    self.playerNP = self.worldNP.attachNewNode(self.player)

    model.reparentTo(self.playerNP)
    model.setZ(-1)
    self.playerNP.setPos(-2, 0, 10)
    # self.playerNP.setH(-90)
    self.playerNP.setCollideMask(BitMask32.allOn())
    self.world.attachCharacter(self.player)

    self.player_x = grid_x
    self.player_y = grid_y
    self.playerNP.setPos(self.level[grid_x][grid_y].getPos())







game = Game()
run()


