
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
    alight.setColor(Vec4(0.05, 0.05, 0.05, 0))
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

  

    # Task
    taskMgr.add(self.update, 'updateWorld')

    # Physics
    self.setup()

    self.directions = { 	
                        'w' : {0:'north', 1:'east', 2:'south', 3:'west'},
                        'a' : {0:'west', 1:'north', 2:'east', 3:'south'},
                        's' : {0:'south', 1:'west', 2:'north', 3:'east'},
                        'd' : {0:'east', 1:'south', 2:'west', 3:'north'},
                        }
    self.current_Orientation = 0 #0-north, 1-east, 2-south, 3 - west     

    self.accept('w',self.spaceCheck, [self.player, 'w'])
    self.accept('s',self.spaceCheck, [self.player, 's'])
    self.accept('a',self.spaceCheck, [self.player, 'a'])
    self.accept('d',self.spaceCheck, [self.player, 'd'])
    #for testing purposes - n
    self.accept('space',self.move, [self.player])
    self.accept('mouse1',self.strike, [self.player])

    self.accept('e',self.rotateCam, ['right'])
    self.accept('q',self.rotateCam, ['left'])

######Cam setup
    self.camNode = self.worldNP.attachNewNode('camnode')
    self.camH = self.camNode.getH()
    self.camTargetH = self.camH               
    base.cam.reparentTo(self.camNode)
    base.cam.setPos(-4,-15,6)
    base.cam.setP(-10)
    base.cam.setH(-10)


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

  def spaceCheck(self,char, dir):
        
        # if char.is_Moving:
        if char.state in char.actionStates:
           return
        direction = self.directions[dir][self.current_Orientation]

        marker_x, marker_y = char.marker_x, char.marker_y
        if direction == 'north':
            marker_y += 1
        elif direction == 'south':
            marker_y -= 1
        elif direction == 'west':
            marker_x -= 1
        elif direction == 'east':
            marker_x += 1

        # cancel if out of bounds
        if marker_x < max(0, char.X_Pos - 1) or marker_x > min(len(self.level), char.X_Pos + 1):
            return
        if marker_y < max(0, char.Y_Pos - 1) or marker_y > min(len(self.level[0]), char.Y_Pos + 1):
            return
        

        char.marker_x, char.marker_y = marker_x, marker_y

        char.moveMarker.reparentTo(render)
        char.marker_target_pos = self.level[char.marker_x][char.marker_y].getPos()
        # char.marker_currentpos = 
        marker_move = LerpPosInterval(char.moveMarker, 0.1, char.marker_target_pos)#, other=self.camNode)
        originalHpr = char.NP.getHpr()
        marker_move.start()

        if marker_x == char.X_Pos and marker_y == char.Y_Pos:
            # don't reset look if on same spot as char
            return
        char.NP.lookAt(LPoint3f(char.marker_target_pos[0], char.marker_target_pos[1], char.marker_target_pos[2]))
        look_pos = char.NP.getHpr()
        char.NP.setHpr(originalHpr)
        # char_look = LerpHprInterval(char.NP, 0.1, look_pos)
        # char_look.start()

        

  def move(self, char):
    #  if char.is_Moving:
     if char.state in char.actionStates:
           return
    #  if char.AP<1:
    #     return
    #  if (self.moveMarker.getPos() - self.player.NP.getPos()).length()< 1:
    #      return
     if char.marker_target_pos ==  char.target_Pos:
           return
    #  print((self.moveMarker.getPos() - char.NP.getPos()).length())
    #  print('curreng',char.current_Pos,'targ',char.target_Pos)
    #  if char.current_Pos == char.target_Pos:
    #     return
     
    #  char.model.play('dodge')


     char.AP -=1
     char.X_Pos, char.Y_Pos = char.marker_x, char.marker_y
     char.target_Pos = self.level[char.X_Pos][char.Y_Pos].getPos()
     char.moveMarker.reparentTo(char.storage)

     char.move()
  
  def strike(self, char):
      if char.state in char.actionStates:
        return
      # if char.AP<2:
      #   return
      
      char.AP-=2
      # char.state = 'strike1'

      # char.moveMarker.reparentTo(char.storage)
      # char.moveMarker.setPos(char.current_Pos)
      # char.target_Pos = char.current_Pos()
  
      if char.marker_target_pos !=  char.current_Pos:
        # char.marker_target_pos =  char.current_Pos
        # char.moveMarker.reparentTo(char.storage)
        # char.moveMarker.setPos(char.current_Pos)
        char.strike()
      else:
         char.marker_target_pos =  char.current_Pos
         char.moveMarker.reparentTo(char.storage)
         char.moveMarker.setPos(char.current_Pos)
         char.feint()
  def rotateCam(self, direction):
    #  ""cam  rotates and soe does coord system of movement""""""
    
    # currentH = self.camNode.getH()
    if direction == 'right':
       self.camTargetH -= 90
       self.current_Orientation +=1
       self.current_Orientation %= 4
    if direction == 'left': 
       self.camTargetH += 90
       self.current_Orientation -=1
       self.current_Orientation %= 4
    #   self.camtargetH = 
    # print(self.current_Orientation)
    

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


    # self.camNode.setH(self.player.NP.getH(render))

    # if h == 0 or h == 270 or h == 90 or h == 180:
    #   self.camNode.setH(self.player.NP.getH(render))
    # self.ap.setText(f'AP:{self.player.AP}')
    self.player.update_Character(dt)
    self.camTask()
    

####display character AP
    if self.player.AP < 1:  
       self.AP1.setAlphaScale(self.player.AP_timer)
       self.AP2.setAlphaScale(.01)
      #  self.AP2_Value = .01
    elif self.player.AP < 2 and self.player.AP >= 1:
       self.AP1.setAlphaScale(1)
       self.AP2.setAlphaScale(self.player.AP_timer)
    elif self.player.AP >= 2:
       self.AP1.setAlphaScale(1)
       self.AP2.setAlphaScale(1)

    return task.cont
  def camTask(self):
    self.camNode.setPos(self.player.NP.getPos(render))
    def limit_angle(angle):
 

      angle %= 360
      if angle < 0:
        angle += 360
      return angle
    # playerh = limit_angle(self.player.targetH)
    # prevh = limit_angle(self.player.currentH)
    self.camH = self.camNode.getH()

    if self.camH != self.camTargetH:
      if self.camH > self.camTargetH:
        self.camH -= 10
      if self.camH < self.camTargetH:
        self.camH += 10
      # print(self.camH)
      self.camNode.setH(self.camH)
    print(limit_angle(self.camH))
    # dh = abs(playerh-prevh)
    # self.camNode.setH()
    # print('camnode platyer h diff',playerh,prevh,dh)

  def cleanup(self):
    self.world = None
    self.worldNP.removeNode()

  def lvl(self, count = 100):
    # block = loader.loadModel('block.glb')
    block = loader.loadModel('post.glb')
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
######COLLISIONS HERE#########

  def collisionSetup(self):
     #sets up collision nodes for charactyers
     #body, atttack, block, 

    traverser = CollisionTraverser('collider')
    base.cTrav = traverser

    self.collHandEvent = CollisionHandlerEvent()
    self.collHandEvent.addInPattern('%fn-into-%in')

    #TODO - do this fore every character
    # for charas in self.characters:

    # traverser.addCollider(character.NP.body_Collision, self.collHandEvemt)
    # traverser.addCollider(character.NP.attack_Collision, self.collHandEvemt)
    # traverser.addCollider(character.NP.Pdodge_Collision, self.collHandEvemt)
    # traverser.addCollider(character.NP.block_Collision, self.collHandEvemt)
    traverser.addCollider(self.player.body_Collision, self.collHandEvent)
    traverser.addCollider(self.player.attack_Collision, self.collHandEvent)
    traverser.addCollider(self.player.Pdodge_Collision, self.collHandEvent)
    traverser.addCollider(self.player.block_Collision, self.collHandEvent)
  
  # def attachHB(self, parent, node, shape, pos=(0, 0, 0), visible=True):
  #     """player hitboxes for attacks/parries"""
  
  
  #     HitB = CollisionCapsule(0, 0.5, 0, 0, 0, 0, 0.5)
  #     node.reparentTo(parent)
  #     node.node().addSolid(shape)
  #     # node.setZ(-.2)
  #     node.setPos(pos)
  
  #     self.attached = True
  #     if visible == True:
  #         node.show()
  # def detachHB(self, node):
  #     node.node().clearSolids()
  #     self.attached = False
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
          ######## player setup
      playermodel = Actor(
              'player/player.bam',
              {
                  'walk': 'player/player_walking.bam',
                  'idle': 'player/player_idle1.bam',
                  'jump': 'player/player_JUMP.bam',
                  'fall': 'player/player_FALL.bam',
                  'land': 'player/player_land.bam',
                  'dodge': 'player/player_evade2.bam',
                  'strike1': 'player/player_strike1L.bam',
                  'feint1': 'player/player_feint1L.bam',
                  'strike2': 'player/player_strike2.bam',
                  'strike3': 'player/player_strike3.bam',
                  'prayer1': 'player/player_pray1.bam',
                  'prayer2': 'player/player_pray2.bam',
                  'takehit': 'player/player_takehit.bam'
              },
          )
  
      self.player = Character(self.worldNP,
                              self.world,
                              playermodel,
                              self.level[0][0].getPos(),
                              loader.loadModel('move_marker.glb'),
                              self.storage
                              )
      # self.moveMarker = loader.loadModel('move_marker.glb')
      # self.moveMarker.setScale(.9)
      # self.moveMarker.reparentTo(self.storage)
      # self.moveMarker.setTransparency(True)
      # self.marker_x = 0
      # self.marker_y = 0
      
      # self.characterSetup(loader.loadModel('guy_static.glb'),
      #                      self.level[0][0].getPos())
      # self.player.characterSetup(loader.loadModel('guy_static.glb'),
      #                      0, 0)
      #hud
      #display AP
      # self.ap = OnscreenText(text = f'AP:{self.player.AP}')
      # self.ap.setPos(-1,-.8)
      self.hud = loader.loadModel('hud.glb')
      self.hud.reparentTo(base.cam)
  
      self.AP1 = self.hud.find('ap1')
      self.AP1.reparentTo(base.cam)
      self.AP1.setTransparency(True)
      self.AP1.setDepthWrite(False)
      # self.AP1.setPos(-1,4,-.9)gy-1
  
      self.AP2 = self.hud.find('ap2')
      self.AP2.reparentTo(base.cam)
      self.AP2.setTransparency(True)
      self.AP2.setDepthWrite(False)
      # self.AP2.setPos(-0.8,4,-.9)
  
      #for character in characters:
      self.collisionSetup()
  
  
  
  


class Character():
  def __init__(
      self,
      worldNP: NodePath,
      world: BulletWorld,
      model,
      startpoint,
      moveMarker,
      storage
      ):
    self.AP = 2
    self.AP_timer=0
    self.world = world
    self.worldNP = worldNP
    self.model = model
    self.startPoint = startpoint

    self.storage = storage

    self.moveMarker = moveMarker
    self.moveMarker.setScale(.9)
    self.moveMarker.reparentTo(self.storage)
    self.moveMarker.setTransparency(True)
    self.marker_x = 0
    self.marker_y = 0
    self.marker_target_pos=None

    self.X_Pos = int(self.startPoint.x)
    self.Y_Pos = int(self.startPoint.y)
    self.current_Pos = Point3(self.X_Pos, self.Y_Pos, 0)
    self.target_Pos = Point3(self.X_Pos, self.Y_Pos, 0)
    self.targetH = 0
    self.currentH = 0
    self.is_Moving = False

    self.pdodgenode = self.worldNP.attachNewNode('pdodge')

    self.state = 'idle'
    self.actionStates = ['dodge', 'strike1', 'feint']
    self.animSeq = None

    

  # def characterSetup(self, model, startpoint):
    # Character
    # h = 1.75
    # w = 0.4
    # shape = BulletCapsuleShape(w, h - 2 * w, ZUp)

    # self.controller = BulletCharacterControllerNode(shape, 0.4, 'Player')
    
    # self.player.setMass(20.0)
    # self.player.setMaxSlope(45.0)
    # self.player.setGravity(9.81)
    self.NP = self.worldNP.attachNewNode('playerNode')

    model.reparentTo(self.NP)
    self.CollSetup()

    self.NP.setPos(self.startPoint)

  def endAction(self):
           self.state = 'idle'

  def move(self):
        self.state = 'dodge'
        #lerp between points
        move = LerpPosInterval(self.NP, 0.3, self.target_Pos)
        # move.start()


        originalHpr = self.NP.getHpr()
        self.NP.lookAt(LPoint3f(self.target_Pos[0], self.target_Pos[1], self.target_Pos[2]))
        look_pos = self.NP.getHpr(render)
        self.NP.setHpr(originalHpr)
        self.currentH = self.NP.getH()
        self.targetH = look_pos.getX()
        adjustedH = self.currentH + ((self.targetH - self.currentH + 180) % 360 - 180)
        look = LerpHprInterval(self.NP, 0.1, (adjustedH, look_pos.getY(), look_pos.getZ()))
        # look.start()

        self.pdodgenode.setPos(self.model.getPos(render))
        attach = Func(self.attachHB,self.pdodgenode,
                                    self.Pdodge_Collision,
                                    CollisionCapsule(0, 0, 0, 0, 0, 5, .5))
        dettach = Func(self.detachHB, self.Pdodge_Collision)
        # self.Pdodge_Collision.show()

        anim = self.model.actorInterval('dodge',
                                        0,
                                        17,
        )


        fin = Func(self.endAction)

        self.animSeq = Sequence(attach,
                                Parallel(anim,
                                         move,
                                         look),
                                Parallel(dettach,fin))
        self.animSeq.start()

  def strike(self):
     self.state = 'strike1'
     anim = self.model.actorInterval('strike1',
                                     0,
                                     25)
     
     fin = Func(self.endAction)

     self.animSeq = Sequence(anim,
                             fin)
     self.animSeq.start()

  def feint(self):
     self.state = 'feint'
     anim = self.model.actorInterval('feint1',
                                     0,
                                     17)
     
     fin = Func(self.endAction)

     self.animSeq = Sequence(anim,
                             fin)
     self.animSeq.start()

  def  update_Character(self, dt):
     
    # self.current_Pos = Point3(self.X_Pos, self.Y_Pos, 0)
    #  self.NP.setPos(self.current_Pos)
    # print('current stat4e:', self.state)
    
    if self.state in self.actionStates:
       return
    self.APreset(dt)
    self.anims()
    

    self.current_Pos = self.NP.getPos(render)

    # print(self.marker_target_pos, self.current_Pos)
    
     #moving
    # if (self.current_Pos - self.target_Pos).length() < 0.01 and self.state=='dodge':
    #    self.state = 'idle'
    #     self.is_Moving = True
    #     #lerp between points
    #     move = LerpPosInterval(self.NP, 0.2, self.target_Pos)
    #     move.start()

    #     originalHpr = self.NP.getHpr()
    #     self.NP.lookAt(LPoint3f(self.target_Pos[0], self.target_Pos[1], self.target_Pos[2]))
    #     look_pos = self.NP.getHpr()
    #     self.NP.setHpr(originalHpr)
    #     currentH = self.NP.getH()
    #     targetH = look_pos.getX()
    #     adjustedH = currentH + ((targetH - currentH + 180) % 360 - 180)
    #     look = LerpHprInterval(self.NP, 0.1, (adjustedH, look_pos.getY(), look_pos.getZ()))
    #     look.start()
    #attacking

    # elif self.state == 'strike1':
    #     print('attacl')
    #     # PLACEHOLDE
    #     frame = self.model.getCurrentFrame()
    #     if frame != None:
    #       if frame>16:
    #         self.state = 'idle'
    # else:
    #     self.is_Moving = False
    #     self.state = 'idle'

    
  def CollSetup(self):
     
      self.body_Collision = self.NP.attachNewNode(
         CollisionNode('body'))
      self.attack_Collision = self.NP.attachNewNode(
         CollisionNode('attack'))
      self.block_Collision = self.NP.attachNewNode(
         CollisionNode('block'))
      self.Pdodge_Collision = self.NP.attachNewNode(
         CollisionNode('Pdodge'))

  def anims(self):
    currentAnim = self.model.getCurrentAnim()
    anim = self.state


    # print(currentAnim)

    # if self.animSeq != None:
         
    #              return

    if anim!=(currentAnim):
       self.model.play(anim)

  def APreset(self, t):
    #  print('ap timer:',self.AP_timer)
    if self.AP <2:
       self.AP_timer+=t
       if self.AP_timer>=1:
          self.AP+=1
          self.AP_timer=0
  
  def attachHB(self, parent, node, shape, pos=(0, 0, 0), visible=True):
      """player hitboxes for attacks/parries"""
  
  
      HitB = CollisionCapsule(0, 0.5, 0, 0, 0, 0, 0.5)
      node.reparentTo(parent)
      node.node().addSolid(shape)
      # node.setZ(-.2)
      node.setPos(pos)
  
      self.attached = True
      if visible == True:
          node.show()
          
  def detachHB(self, node):
      node.node().clearSolids()
      self.attached = False

    # if self.AP < 1:  
    #    self.plane.setAlphaScale(self.AP_timer)
    #    self.AP2.setAlphaScale(.01)
    #   #  self.AP2_Value = .01
    # elif self.AP < 2 and self.AP >= 1:
    #    self.plane.setAlphaScale(1)
    #    self.AP2.setAlphaScale(self.AP_timer)
    # elif self.AP >= 2:
    #    self.plane.setAlphaScale(1)
    #    self.AP2.setAlphaScale(1)

       
  
       

game = Game()
run()


