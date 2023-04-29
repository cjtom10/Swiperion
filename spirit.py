from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject
from direct.interval.LerpInterval import LerpFunc
from direct.interval.IntervalGlobal import Sequence, Parallel, Func, Wait
from direct.interval.LerpInterval import *
from direct.interval.ActorInterval import ActorInterval, LerpAnimInterval
from panda3d.bullet import *
from panda3d.core import *


class Spirit(DirectObject):
    def __init__(self, world, worldNP, playerM):
        # self.model = loader.loadModel("")  # Load spirit model
        # self.model.reparentTo(render)  # Reparent spirit to render
        # self.model.setColorScale(1, 0, 0, 1)  # Set spirit color to red
        spirit_shape = BulletCapsuleShape(0.5, 1,1)
        spirit_node = BulletRigidBodyNode('Capsule')
        spirit_node.setMass(1.0)
        spirit_node.addShape(spirit_shape)
        self.spirit_np = worldNP.attachNewNode(spirit_node)
        self.spirit_np.setPos(0,10,5)
        world.attachRigidBody(spirit_node)

        self.moveSequence = None  # Initialize move sequence to None
        self.playerPositions = []  # Initialize list of player positions\
        self.initialChasePos = None
        self.isMoving = False  # Initialize moving flag to False
        self.decideTarget(playerM)
        # self.takeAction()  # Start chasing the player

    def decideTarget(self, playerM):
        spirit_to_player_dist = self.spirit_np.getPos() - playerM.getPos()
        spirit_to_possessed_dist = 99999999999 #TODO update later 
        if spirit_to_player_dist < spirit_to_possessed_dist:
            self.initialChasePos = playerM.getPos()
        else:
            # slef.char_to_move_to
            pass

    def takeAction(self):
        if self.isMoving:
            return  # Return if already moving towards a player position

        # TODO change to model
        # startPos = self.model.getPos()  # Get current spirit position
        startPos = self.spirit_np.getPos()
        endPos = self.initialChasePos  
        distance = (endPos - startPos).length()  
        time = distance / 2.0  
        self.isMoving = True  
        self.moveSequence = Sequence( 
            LerpPosInterval(self.spirit_np, time, endPos),
            Func(self.onMoveFinished)  # Call onMoveFinished when move sequence finishes
        )
        self.moveSequence.start()  

    def onMoveFinished(self):
        self.isMoving = False  # Set moving flag to False
        self.spirit_np.setPos(9999,9999,9999)
        # TODO what to do when reached position
    
    def die(self):
        pass
