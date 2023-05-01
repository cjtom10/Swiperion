import random

from direct.actor.Actor import Actor
from direct.showbase.ShowBase import ShowBase
from panda3d.ai import AICharacter, AIWorld
from panda3d.bullet import (BulletCylinderShape, BulletRigidBodyNode,
                            BulletWorld, ZUp)
from panda3d.core import (BitMask32, CollisionNode, CollisionSphere, NodePath,
                          Vec3)

CYLINDER_SHAPE = BulletCylinderShape(0.5, 2.4, ZUp)

Z_OUT_OF_BOUNDS = -1000


class Vessel:
    def __init__(
        self,
        taskMgr,
        name,
        worldNP: NodePath,
        world: BulletWorld,
        aiWorld: AIWorld,
        player: NodePath,
        is_possessed=False,
    ) -> None:
        self.taskMgr = taskMgr
        self.name = name

        self.body = worldNP.attachNewNode(BulletRigidBodyNode('Cylinder'))
        self.body.node().setMass(1.0)
        self.body.node().addShape(CYLINDER_SHAPE)
        self.body.setPos(
            random.randrange(-20, 20), random.randrange(30, 50), 3
        )
        self.body.setHpr(0, 0, 0)
        self.body.setCollideMask(BitMask32.allOn())
        world.attachRigidBody(self.body.node())

        self.vessel_model = Actor(
            'johnooi/johnooi.bam',
            {
                'idle': 'johnooi/johnooi_Idle.bam',
                'walk': 'johnooi/johnooi_walk.bam',
            },
        )
        self.vessel_model.setHpr(180, 0, 0)
        self.vessel_model.loop('idle')
        self.vessel_model.reparentTo(self.body)
        self.vessel_model.setZ(-1.2)
        self.vessel_model.setScale(0.6)
        self.vessel_model.loop('walk')

        self.possessed_model = Actor(
            'models/possessed.bam',
            {
                'spawn': 'models/possessed_spawn.bam',
                'run': 'models/possessed_run.bam',
                'slash1': 'models/possessed_slash1.bam',
                'slash2': 'models/possessed_slash2.bam',
                'stab': 'models/possessed_stab.bam',
                'deflected': 'models/possessed_deflected.bam',
                'death': 'models/possessed_death.bam',
            },
        )
        self.possessed_model.setHpr(180, 0, 0)
        self.possessed_model.loop('spawn')
        self.possessed_model.reparentTo(self.body)
        self.possessed_model.setZ(Z_OUT_OF_BOUNDS)
        self.possessed_model.setScale(0.3)
        # attach claws
        self.rclaw_model = loader.loadModel('possessed/claw.glb')
        hand_joint = self.possessed_model.exposeJoint(
            None, 'modelRoot', 'Hand.R'
        )
        self.rclaw_model.reparentTo(hand_joint)
        self.rclaw_model.setPos(0, 0, 0)
        self.rclaw_model.setScale(0.3)
        self.lclaw_model = loader.loadModel('possessed/claw.glb')
        hand_joint = self.possessed_model.exposeJoint(
            None, 'modelRoot', 'Hand.L'
        )
        self.lclaw_model.reparentTo(hand_joint)
        self.lclaw_model.setPos(0, 0, 0)
        self.lclaw_model.setScale(0.3)

        self.hitbox = self.body.attachNewNode(CollisionNode('hit'))
        sphere = CollisionSphere(0, 0, 0, 1)
        self.hitbox.node().addSolid(sphere)

        sphere = CollisionSphere(0, 2, 0, 1.5)
        self.lclaw_hitbox = self.lclaw_model.attachNewNode(
            CollisionNode('claw_hit')
        )
        self.lclaw_hitbox.node().addSolid(sphere)
        self.rclaw_hitbox = self.rclaw_model.attachNewNode(
            CollisionNode('claw_hit')
        )
        self.rclaw_hitbox.node().addSolid(sphere)

        # TODO: rm, debug only to show hitbox
        # self.hitbox.show()
        self.lclaw_hitbox.show()
        self.rclaw_hitbox.show()

        self.aiWorld = aiWorld
        self.player = player
        self.aiChar = AICharacter(repr(self), self.body, 100, 0.5, 5)
        self.aiWorld.addAiChar(self.aiChar)
        self.aiBehaviors = self.aiChar.getAiBehaviors()

        self.attack_methods = {
            'slash1': self.slash1,
            'stab': self.stab,
        }

        self.is_possessed = is_possessed
        self.state = 'pursue'

    def is_playing_any(self, *anims):
        current_anim = self.possessed_model.getCurrentAnim()
        return any(current_anim == anim for anim in anims)

    def is_player_in_range(self, distance: int = 5):
        player_pos = self.player.getPos(render)
        vessel_pos = self.possessed_model.getPos(render)
        return (player_pos - vessel_pos).length() <= distance

    def pursue_player(self, task=None):
        self.aiBehaviors.pursue(self.player)
        if self.possessed_model.getCurrentAnim() == 'run':
            return
        self.possessed_model.loop('run')

    def pursue_player(self, task=None):
        if self.is_playing_any('run'):
            return
        self.aiBehaviors.pursue(self.player)
        self.possessed_model.loop('run')

    def attack(self, task=None):
        attack = random.choice(list(self.attack_methods.keys()))
        self.attack_methods[attack]()
        self.state = 'attack'

    def slash1(self):
        if self.is_playing_any('slash1'):
            return
        self.possessed_model.play('slash1')
        self.taskMgr.doMethodLater(
            self.possessed_model.getDuration('slash1'),
            self.slash1_post,
            f'{self.name}_slash2_or_pursue',
        )

    def slash2(self):
        if self.is_playing_any('slash2'):
            return
        self.possessed_model.play('slash2')
        self.taskMgr.doMethodLater(
            self.possessed_model.getDuration('slash2'),
            self.attack_post,
            f'{self.name}_attack_or_pursue',
        )
        self.state = 'pursue'

    def stab(self):
        if self.is_playing_any('stab'):
            return
        self.possessed_model.play('stab')
        self.taskMgr.doMethodLater(
            self.possessed_model.getDuration('stab'),
            self.attack_post,
            f'{self.name}_attack_or_pursue',
        )
        self.state = 'pursue'

    def slash1_post(self, task=None):
        self.slash2() if self.is_player_in_range() else self.pursue_player()

    def attack_post(self, task=None):
        self.attack() if self.is_player_in_range() else self.pursue_player()

    def update(self, task=None):
        if not self.is_possessed:
            self.aiBehaviors.wander()
            return

        # wait for attack to finish
        if self.state == 'attack':
            return

        distance_to_player = (
            self.body.getPos(render) - self.player.getPos(render)
        ).length()

        if distance_to_player > 5:
            self.pursue_player()
        else:
            self.attack()

    @property
    def is_possessed(self):
        return self._is_possessed

    @is_possessed.setter
    def is_possessed(self, is_possessed: bool):
        # a little magical but oh well
        self._is_possessed = is_possessed
        if is_possessed:
            self.possessed_model.setZ(-1)
            self.vessel_model.setZ(Z_OUT_OF_BOUNDS)
        else:
            self.possessed_model.setZ(Z_OUT_OF_BOUNDS)
            self.vessel_model.setZ(-1.2)
