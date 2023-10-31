
from pandac.PandaModules import loadPrcFileData
loadPrcFileData('', 'win-size 1280 768')
loadPrcFileData('', 'sync-video t')

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

from gpadinput import GamepadInput

import gltf
import simplepbr

import math
import random

class Game(DirectObject, GamepadInput):

  def __init__(self):
    base.setBackgroundColor(0.1, 0.1, 0.8, 1)
    base.setFrameRateMeter(True)
    

    # base.cam.setPos(0, -20, 4)
    # base.cam.lookAt(0, 0, 0)

    pipeline = simplepbr.init()
    pipeline.use_normal_maps = True
    pipeline.use_occlusion_maps = True
    # gltf.patch_loader(loader)

    # Light
    alight = AmbientLight('ambientLight')
    alight.setColor(Vec4(0.5, 0.5, 0.5, 0))
    alightNP = render.attachNewNode(alight)

    dlight = DirectionalLight('directionalLight')
    dlight.setDirection(Vec3(1, 1, -1))
    dlight.setColor(Vec4(0.7, 0.7, 0.7, 1))
    dlightNP = render.attachNewNode(dlight)

    # render.clearLight()
    # render.setLight(alightNP)
    # render.setLight(dlightNP)

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
                        'up' : {0:'north', 1:'east', 2:'south', 3:'west'},
                        'left' : {0:'west', 1:'north', 2:'east', 3:'south'},
                        'down' : {0:'south', 1:'west', 2:'north', 3:'east'},
                        'right' : {0:'east', 1:'south', 2:'west', 3:'north'},
                        }
      

    self.accept('w',self.spaceCheck, [self.player, 'up'])
    self.accept('s',self.spaceCheck, [self.player, 'down'])
    self.accept('a',self.spaceCheck, [self.player, 'left'])
    self.accept('d',self.spaceCheck, [self.player, 'right'])
    #for testing purposes - n
    self.accept('space',self.move, [self.player])
    self.accept('mouse1',self.strike, [self.player])

    self.accept('e',self.rotateCam, [self.player,'right'])
    self.accept('q',self.rotateCam, [self.player,'left'])


    self.actionCosts = {
                        'strike':2,
                        'move':1,
                        'block':1

    }
  
    GamepadInput.__init__(self)
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
        direction = self.directions[dir][char.current_Orientation]

        marker_x, marker_y = char.marker_x, char.marker_y
        if direction == 'north':
            marker_y += 1
        elif direction == 'south':
            marker_y -= 1
        elif direction == 'west':
            marker_x -= 1
        elif direction == 'east':
            marker_x += 1

        print('x, y  pos',char.X_Pos, char.Y_Pos)
        # cancel if out of bounds
        if marker_x < max(0, char.X_Pos - 1) or marker_x > min(len(self.level), char.X_Pos + 1):

            return
        if marker_y < max(0, char.Y_Pos - 1) or marker_y > min(len(self.level[0]), char.Y_Pos + 1):
            
            return
        

        char.marker_x, char.marker_y = marker_x, marker_y

        char.moveMarker.reparentTo(render)
        # char.moveMarker.setPos(char.NP.getPos())
        char.marker_target_pos = self.level[char.marker_x][char.marker_y].getPos()
        # char.marker_currentpos = 
        marker_move = LerpPosInterval(char.moveMarker, 0.1, char.marker_target_pos)#, other=render)
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

  def rotateCam(self,char, direction):
    #  ""cam  rotates and soe does coord system of movement""""""
    
    # currentH = self.camNode.getH()
    if direction == 'right':
       char.camTargetH -= 90
       char.current_Orientation +=1
       char.current_Orientation %= 4
    if direction == 'left': 
       char.camTargetH += 90
       char.current_Orientation -=1
       char.current_Orientation %= 4        

  def move(self, char):
    #  if char.is_Moving:
     if char.state in char.actionStates:
           return
     if char.AP<self.actionCosts['move']:
        return
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
      if char.AP<self.actionCosts['strike']:
        
        return
      
      char.AP-=2
      currentX = char.X_Pos
      currentY = char.Y_Pos
      char.X_Pos, char.Y_Pos = char.marker_x, char.marker_y
      char.target_Pos = self.level[char.X_Pos][char.Y_Pos].getPos()
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
        #  char.marker_target_pos =  char.current_Pos
        #  char.moveMarker.reparentTo(char.storage)
        #  char.moveMarker.setPos(char.current_Pos)
         char.feint()
      
      char.target_Pos =  char.current_Pos
      char.marker_target_pos =  char.current_Pos
      char.moveMarker.reparentTo(char.storage)
      char.moveMarker.setPos(char.current_Pos)
      char.marker_x, char.marker_y, char.X_Pos, char.Y_Pos = currentX, currentY, currentX, currentY
 




######COLLISION EVENTS HERE
  def takeHit(self,hitter,hittee, entry):
     if hittee.isHit == True:
        return
     hittee.isHit  = True
     hittee.state = 'isHit'

     hitter.state = 'hasHit'

     print(hitter.name, ' hits', hittee.name)  
     hitter.attack_Collision.node().clearSolids()
     end1 = Func(hittee.endAction)
     end2 = Func(hitter.endAction)
   # sequence: hittee state = takehit
  #  hitter state = hashit
     def twitch(p,e):
            #TODO add an anim instead of this
            torso=hittee.model.controlJoint(None, "modelRoot", "torso")
            torso.setP(p)
            if e == True:
              hittee.model.releaseJoint("modelRoot", "torso")
     

     a = Func(twitch, -10, False)
     b = Func(twitch, 0, True)
     p = Func(hitter.animSeq.pause)#### player hitstopping
     r = Func(hitter.animSeq.resume)

     hitseq = Sequence(a, p, Wait(.1),b, r,end1,end2).start()

  def dodgeInto(self,hitter,hittee, entry):
    #  if hitter.state == 'strike1':
    #   return
    #  if hittee.isHit == True:
    #     return
    #  hittee.isHit  = True
     print(hitter.name, ' dodges intor', hittee.name)  
    #  if self.player.state == 'dodging' and self.player2.state!= 'dodging':s
     
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


    self.player.update_Character(dt)
    self.player2.update_Character(dt)
    self.player.camTask()
    self.player2.camTask()

    

    # print('p1 spotq', self.player2.X_Pos,self.player2.Y_Pos)

####display character Hud
#playewr one
    if self.player.AP < 1:  
       self.P1AP1.setAlphaScale(self.player.AP_timer)
       self.P1AP2.setAlphaScale(.01)
      #  self.AP2_Value = .01
    elif self.player.AP < 2 and self.player.AP >= 1:
       self.P1AP1.setAlphaScale(1)
       self.P1AP2.setAlphaScale(self.player.AP_timer)
    elif self.player.AP >= 2:
       self.P1AP1.setAlphaScale(1)
       self.P1AP2.setAlphaScale(1)
#playewr 2
    if self.player2.AP < 1:  
       self.P2AP1.setAlphaScale(self.player2.AP_timer)
       self.P2AP2.setAlphaScale(.01)
      #  self.AP2_Value = .01
    elif self.player2.AP < 2 and self.player2.AP >= 1:
       self.P2AP1.setAlphaScale(1)
       self.P2AP2.setAlphaScale(self.player2.AP_timer)
    elif self.player.AP >= 2:
       self.P2AP1.setAlphaScale(1)
       self.P2AP2.setAlphaScale(1)

    return task.cont


  def cleanup(self):
    self.world = None
    self.worldNP.removeNode()
  
  def camSetup(self, splitscreen = True):
    """set up cam for single player or splitscreen"""

    # self.p1Cam = base.camList[0]
    # base.disableMouse()
    camStore = NodePath('camerazoo')
    camStore.setZ(-50000)

    if splitscreen == False:
      self.p1Cam = base.camList[0]
      self.p2Cam = None
      self.camNode = self.player.camNode
      # self.camH = self.camNode.getH()
      # self.camTargetH = self.camH               
      self.p1Cam.reparentTo(self.camNode)
      self.p1Cam.setPos(0,-15,8)
      self.p1Cam.setP(-15)
      self.p1Cam.setH(-10)

#####NEED TO DISTINGUISH p1/p2 hud
      self.p1Hud = self.p1Cam.attachNewNode('hud')#only visible by p1 cam
      hud = loader.loadModel('hud.glb')
      hud.reparentTo(self.p1Hud)
  
      self.P1AP1 = hud.find('ap1')
      self.P1AP1.reparentTo(self.p1Hud)
      self.P1AP1.setTransparency(True)
      self.P1AP1.setDepthWrite(True)
  
      self.P1AP2 = hud.find('ap2')
      self.P1AP2.reparentTo(self.p1Hud)
      self.P1AP2.setTransparency(True)
      self.P1AP2.setDepthWrite(True)

      self.p1HP = []
      for i in range(4):
         self.p1HP.append(self.hud.find(f'hp{i}'))
      print(self.p1HP)
    elif splitscreen == True:
      c1 =base.makeCamera(base.win, displayRegion=(0,.5,0,1))
      c2 = base.makeCamera(base.win, displayRegion=(.5,1,0,1))
      c1.node().getLens().setFov(40, 40)
      c2.node().getLens().setFov(40, 40)

      base.camList[0].reparentTo(camStore)

      self.p1Cam = base.camList[2]
      self.p2Cam = base.camList[1]
      
      base.camList[0].reparentTo(self.storage)
      # print(base.camList)

      self.camNode = self.player.camNode
      self.camNode2 = self.player2.camNode
      # self.camH = self.camNode.getH()
      # self.camTargetH = self.camH               
      self.p1Cam.reparentTo(self.camNode)
      self.p1Cam.setPos(0,-15,8)
      self.p1Cam.setP(-15)
      self.p1Cam.setH(-10)

      self.p2Cam.reparentTo(self.camNode2)
      self.p2Cam.setPos(0,-15,8)
      self.p2Cam.setP(-15)
      self.p2Cam.setH(-10)

 ######HUD 
 #p1


      self.p1Hud = self.p1Cam.attachNewNode('hud')#only visible by p1 cam
      hud = loader.loadModel('hud.glb')
      hud.reparentTo(self.p1Hud)

      self.p1HP = []
      for i in range(1,5):
         self.p1HP.append(hud.find(f'hp{i}'))
   

      self.P1AP1 = hud.find('ap1')
      self.P1AP1.reparentTo(self.p1Hud)
      self.P1AP1.setTransparency(True)
      self.P1AP1.setDepthWrite(True)
  
      self.P1AP2 = hud.find('ap2')
      self.P1AP2.reparentTo(self.p1Hud)
      self.P1AP2.setTransparency(True)
      self.P1AP2.setDepthWrite(True)   
 #p2
      self.p2Hud = self.p2Cam.attachNewNode('hud')#only visible by p1 cam
      hud2 = loader.loadModel('hud.glb')
      hud2.reparentTo(self.p2Hud)

      self.p2HP = []
      for i in range(1,5):
         self.p2HP.append(hud.find(f'hp{i}'))
    

      self.P2AP1 = hud2.find('ap1')
      self.P2AP1.reparentTo(self.p2Hud)
      self.P2AP1.setTransparency(True)
      self.P2AP1.setDepthWrite(True)
  
      self.P2AP2 = hud2.find('ap2')
      self.P2AP2.reparentTo(self.p2Hud)
      self.P2AP2.setTransparency(True)
      self.P2AP2.setDepthWrite(True)   
   
   # hide hud elements from eacho ther   
      p1Mask = BitMask32.bit(1)
      p2Mask = BitMask32.bit(2)

      self.p1Cam.node().setCameraMask(p1Mask)
      self.p2Cam.node().setCameraMask(p2Mask)

      self.player.moveMarker.hide(p2Mask)
      self.player2.moveMarker.hide(p1Mask)
      self.p1Hud.hide(p2Mask)
      self.p2Hud.hide(p1Mask)

  def lvl(self, count = 100):
    # block = loader.loadModel('block.glb')
    block = loader.loadModel('post.glb')
    spike = loader.loadModel('spike1.glb')
    # block.reparentTo(self.worldNP)

    rock1 = loader.loadModel('rock1.glb')
    rock2 = loader.loadModel('rock2.glb')
    rock3 = loader.loadModel('rock3.glb')
    rock4 = loader.loadModel('rock4.glb')
    rock5 = loader.loadModel('rock5.glb')
    rocks = [rock1,
            rock2,
            rock3,
            rock4,
            rock5]
    # for i in rocks:
    #    i.reparentTo(self.worldNP)

    size = 20
    spacing = 3
    nodeCount = count

    self.level = []


      
      # tile.setX(i+1)
    for x in range(0, size, spacing):
          self.level.append([])
          for y in range(0, size, spacing):
             
              tile = self.worldNP.attachNewNode(f'tile_{x}_{y}')
              
              tile.setPos(x,y,0)
              self.level[-1].append(tile)
              rok = rocks[random.randint(0,4)]
              # rok.instanceTo(tile)
              spike.instanceTo(tile)
              spike.setH(random.randint(0, 359))
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
    for Cnode in self.player.collisionNodes:
       traverser.addCollider(Cnode, self.collHandEvent)
    for Cnode in self.player2.collisionNodes:
       traverser.addCollider(Cnode, self.collHandEvent)
    # traverser.addCollider(self.player.body_Collision, self.collHandEvent)
    # traverser.addCollider(self.player.attack_Collision, self.collHandEvent)
    # traverser.addCollider(self.player.Pdodge_Collision, self.collHandEvent)
    # traverser.addCollider(self.player.block_Collision, self.collHandEvent)

    for P1bodypart in self.player.playerHB:
                  #hit player
                  self.accept(
                    f'{self.player2.name}attack-into-{P1bodypart.name}',
                    self.takeHit,
                    extraArgs=[self.player2,
                               self.player])
                  #dodge into stationary player
                  for P2bodypart in self.player2.playerHB:
                    self.accept(
                      f'{P1bodypart.name}-into-{P2bodypart.name}',
                      self.dodgeInto,
                      extraArgs=[self.player,
                                 self.player2])
                     
    for bodypart in self.player2.playerHB:
                  #hit player
                  self.accept(
                    f'{self.player.name}attack-into-{bodypart.name}',
                    self.takeHit,
                    extraArgs=[self.player,
                               self.player2])
                  #dodge into stationary player
                  for P1bodypart in self.player.playerHB:
                    self.accept(
                      f'{bodypart.name}-into-{P1bodypart.name}',
                      self.dodgeInto,
                      extraArgs=[self.player,
                                 self.player2])
    
    # for bodypart in self.player2.playerHB:  
  
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
                  'dodge': 'player/player_evade3.bam',
                  'strike1': 'player/player_strike1L.bam',
                  'feint1': 'player/player_feint1L.bam',
                  'strike2': 'player/player_strike2.bam',
                  'strike3': 'player/player_strike3.bam',
                  'prayer1': 'player/player_pray1.bam',
                  'prayer2': 'player/player_pray2.bam',
                  'takehit': 'player/player_takehit.bam'
              },
          )
      player2model = Actor(
              'player/player2.bam',
              {
                  'walk': 'player/player2_walking.bam',
                  'idle': 'player/player2_idle.bam',
                  'jump': 'player/player2_JUMP.bam',
                  'fall': 'player/player2_FALL.bam',
                  'land': 'player/player2_land.bam',
                  'dodge': 'player/player2_evade2.bam',
                  'strike1': 'player/player2_strike1L.bam',
                  'feint1': 'player/player2_feint1L.bam',
                  'strike2': 'player/player2_strike2.bam',
                  'strike3': 'player/player2_strike3.bam',
                  'prayer1': 'player/player2_pray1.bam',
                  'prayer2': 'player/player2_pray2.bam',
                  'takehit': 'player/player2_takehit.bam'
              },
          )
  
      self.player = Character(self.worldNP,
                              self.world,
                              'player1',
                              playermodel,
                              4,
                              6,
                              self.level,
                              loader.loadModel('move_marker.glb'),
                              self.storage,
                              0
                              )
      self.player2 = Character(self.worldNP,
                              self.world,
                              'player2',
                              player2model,
                              0,
                              0,
                              self.level,
                              loader.loadModel('move_marker.glb'),
                              self.storage,
                              180
                              )



      self.camSetup()


      #for character in characters:
      self.collisionSetup()
  
  
  
  


class Character():
  def __init__(
      self,
      worldNP: NodePath,
      world: BulletWorld,
      name,
      model,
      startX,
      startY,
      lvl,
      moveMarker,
      storage,
      startH
      ):
    
    self.HP = 4
    self.AP = 2
    self.AP_timer=0
    self.world = world
    self.worldNP = worldNP
    self.model = model
    self.startPoint = lvl[startX][startY].getPos()

    self.storage = storage
    self.name = name

    self.moveMarker = moveMarker
    self.moveMarker.setScale(.9)
    self.moveMarker.reparentTo(self.storage)
    self.moveMarker.setTransparency(True)
    self.marker_x = startX
    self.marker_y = startY
    self.marker_target_pos=None

    self.X_Pos = int(self.startPoint.x)
    self.Y_Pos = int(self.startPoint.y)
    self.current_Pos = Point3(self.X_Pos, self.Y_Pos, 0)
    self.target_Pos = Point3(self.X_Pos, self.Y_Pos, 0)
    self.targetH = 0
    self.currentH = startH
    self.is_Moving = False

    self.pdodgenode = self.worldNP.attachNewNode('pdodge')
    self.handR = self.model.expose_joint(None, 'modelRoot', 'Hand.R')
    self.handL = self.model.expose_joint(None, 'modelRoot', 'Hand.L')


    self.state = 'idle'
    self.actionStates = ['dodge', 
                         'strike1', 
                         'feint',
                         'block',
                         'isHit']
    self.animSeq = None

    self.isHit = False

    self.camTargetH = 0
    self.camNode = worldNP.attachNewNode('camnode')
    self.current_Orientation = 0 #0-north, 1-east, 2-south, 3 - west   
    

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

    self.NP.setH(startH)

    model.reparentTo(self.NP)
    self.CollSetup()

    self.NP.setPos(self.startPoint)
    self.moveMarker.setPos(self.startPoint)

  def endAction(self):
           self.state = 'idle'
           self.animSeq = None
           self.isHit = False
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

#####ACTIONS HERE
  def strike(self):
    #attach from frame 9 to 20
     self.state = 'strike1'
     a1 = self.model.actorInterval('strike1',
                                     startFrame=0,
                                     endFrame=8)
     a2 = self.model.actorInterval('strike1',
                                     startFrame=9,
                                     endFrame=20)
     a3 = self.model.actorInterval('strike1',
                                     startFrame=21,
                                     endFrame=40)
     
     
     originalHpr = self.NP.getHpr()
     self.NP.lookAt(LPoint3f(self.target_Pos[0], self.target_Pos[1], self.target_Pos[2]))
     look_pos = self.NP.getHpr(render)
     self.NP.setHpr(originalHpr)
     self.currentH = self.NP.getH()
     self.targetH = look_pos.getX()
     adjustedH = self.currentH + ((self.targetH - self.currentH + 180) % 360 - 180)
     look = LerpHprInterval(self.NP, 0.1, (adjustedH, look_pos.getY(), look_pos.getZ()))
     attach = Func(self.attachHB,self.handR,
                                 self.attack_Collision,
                                #  CollisionSphere(0, 0, 0,.5)
                                CollisionCapsule(0,0,0,0,0,2,.5))
     dettach = Func(self.detachHB, self.attack_Collision)

     fin = Func(self.endAction)

     self.animSeq = Sequence(a1,
                             Parallel(attach,
                              look,
                             a2),
                             dettach,
                             a3,
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

  def takeDmg(self):
     print('yeeeowch')
    #  self.isHit = True
  
  def camTask(self):
    self.camNode.setPos(self.NP.getPos(render))
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
  def  update_Character(self, dt):

    
    if self.state in self.actionStates:
       return
    self.APreset(dt)
    self.anims()
    

    self.current_Pos = self.NP.getPos(render)

####SETUP HERE

    
  def CollSetup(self,HBvisible=True):
      self.playerHB = []
      self.isHit = False
      self.isStunned=False
      self.collisionNodes = []

      self.body_Collision = self.NP.attachNewNode(
         CollisionNode(f'{self.name}body'))
      self.collisionNodes.append(self.body_Collision)
      self.attack_Collision = self.NP.attachNewNode(
         CollisionNode(f'{self.name}attack'))
      self.collisionNodes.append(self.attack_Collision)
      self.block_Collision = self.NP.attachNewNode(
         CollisionNode(f'{self.name}block'))
      self.collisionNodes.append(self.block_Collision)
      self.Pdodge_Collision = self.NP.attachNewNode(
         CollisionNode(f'{self.name}Pdodge'))
      self.collisionNodes.append(self.Pdodge_Collision)
      
      
     
      # positions for collision soluids
      self.head = self.model.expose_joint(None, 'modelRoot', 'Bone.004')
      self.chest = self.model.expose_joint(None, 'modelRoot', 'chest')
      rightbicep = self.model.expose_joint(None, 'modelRoot', 'bicep.R')
      # self.rightfoot = self.model.expose_joint(None, 'modelRoot', 'foot.R')
      # self.leftfoot = self.model.expose_joint(None, 'modelRoot', 'foot.L')
      rightforearm = self.model.expose_joint(None, 'modelRoot', 'forarm.R')
      rightthigh = self.model.expose_joint(None, 'modelRoot', 'femur.R')
      rightshin = self.model.expose_joint(None, 'modelRoot', 'shin.R')
      leftbicep = self.model.expose_joint(None, 'modelRoot', 'bicep.L')
      leftforearm = self.model.expose_joint(None, 'modelRoot', 'forarm.L')
      leftthigh = self.model.expose_joint(None, 'modelRoot', 'femur.L')
      leftshin = self.model.expose_joint(None, 'modelRoot', 'shin.L')
      # collision solides
      headHB = CollisionSphere(0, 0, 0, 0.2)
      chestHB = CollisionCapsule((0, 0, 0), (0, 0, 0.7), 0.4)
      arm = CollisionCapsule((0, 0, 0), (0, 0, 0.7), 0.1)
      leg = CollisionCapsule((0, 0, 0), (0, 0, .8), 0.1)
      # attach the solidss
      self.headHB = self.head.attachNewNode(CollisionNode(f'{self.name}head'))
      self.headHB.node().addSolid(headHB)
      self.headHB.setZ(0.2)
      # self.headHB.show()
      self.playerHB.append(self.headHB)
      self.chestHB = self.chest.attachNewNode(CollisionNode(f'{self.name}rchest'))
      self.chestHB.node().addSolid(chestHB)
      self.chestHB.setY(-0.2)
      self.playerHB.append(self.chestHB)
      self.bicepR = rightbicep.attachNewNode(CollisionNode(f'{self.name}bicepr'))
      self.bicepR.node().addSolid(arm)
      # self.bicepR.show()
      self.playerHB.append(self.bicepR)
      self.forarmR = rightforearm.attachNewNode(
          CollisionNode(f'{self.name}forearmr')
      )
      self.forarmR.node().addSolid(arm)
      # self.forarmR.show()
      self.playerHB.append(self.forarmR)
      self.thighR = rightthigh.attachNewNode(CollisionNode(f'{self.name}thighr'))
      self.thighR.node().addSolid(leg)
      # self.thighR.show()
      self.playerHB.append(self.thighR)
      self.shinR = rightshin.attachNewNode(CollisionNode(f'{self.name}shinr'))
      self.shinR.node().addSolid(leg)
      # self.shinR.show()
      self.playerHB.append(self.shinR)
      self.bicepL = leftbicep.attachNewNode(CollisionNode(f'{self.name}bicepl'))
      self.bicepL.node().addSolid(arm)
      # self.bicepL.show()
      self.playerHB.append(self.bicepL)
      self.forarmL = leftforearm.attachNewNode(
          CollisionNode(f'{self.name}forearml')
      )
      self.forarmL.node().addSolid(arm)
      # self.forarmL.show()
      self.playerHB.append(self.forarmL)
      self.thighL = leftthigh.attachNewNode(CollisionNode(f'{self.name}thighl'))
      self.thighL.node().addSolid(leg)
      # self.thighL.show()
      self.playerHB.append(self.thighL)
      self.shinL = leftshin.attachNewNode(CollisionNode(f'{self.name}shinl'))
      self.shinL.node().addSolid(leg)
      # self.shinL.show()
      self.playerHB.append(self.shinL)


      for bodyPart in self.playerHB:
         self.collisionNodes.append(bodyPart)

      if HBvisible == True:
          for node in self.playerHB:
              node.show()
  def anims(self):
    currentAnim = self.model.getCurrentAnim()
    anim = self.state


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

       

game = Game()
run()


