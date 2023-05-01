import random

from direct.actor.Actor import Actor
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
        worldNP: NodePath,
        world: BulletWorld,
        aiWorld: AIWorld,
        player: NodePath,
        is_possessed=False,
    ) -> None:
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
        # TODO: could dynamically switch back to idle, but it will always be moving or about.coming
        self.vessel_model.loop('walk')

        self.possessed_model = Actor(
            'possessed/possessed.bam',
            {
                'spawn': 'possessed/possessed_spawn.bam',
                'run': 'possessed/possessed_run.bam',
                'slash1': 'possessed/possessed_slash1.bam',
                'slash2': 'possessed/possessed_slash2.bam',
                'stab': 'possessed/possessed_stab.bam',
                'deflected': 'possessed/possessed_deflected.bam',
                'death': 'possessed/possessed_death.bam',
            },
        )
        self.possessed_model.setHpr(180, 0, 0)
        self.possessed_model.loop('spawn')
        self.possessed_model.reparentTo(self.body)
        self.possessed_model.setZ(Z_OUT_OF_BOUNDS)
        self.possessed_model.setScale(0.3)

        self.hitbox = self.body.attachNewNode(CollisionNode('hit'))
        sphere = CollisionSphere(0, 0, 0, 1)
        self.hitbox.node().addSolid(sphere)

        self.aiWorld = aiWorld
        self.player = player
        self.aiChar = AICharacter(repr(self), self.body, 100, 0.5, 5)
        self.aiWorld.addAiChar(self.aiChar)
        self.aiBehaviors = self.aiChar.getAiBehaviors()

        self.is_possessed = is_possessed

    def update(self):
        if self.is_possessed:
            if self.possessed_model.getCurrentAnim() != 'run':
                self.possessed_model.loop('run')
            self.aiBehaviors.pursue(self.player)
        else:
            self.aiBehaviors.wander()

    @property
    def is_possessed(self):
        return self._is_possessed

    @is_possessed.setter
    def is_possessed(self, is_possessed: bool):
        # a little magical but oh well
        self._is_possessed = is_possessed
        if (is_possessed):
            self.possessed_model.setZ(-1)
            self.vessel_model.setZ(Z_OUT_OF_BOUNDS)
        else:
            self.possessed_model.setZ(Z_OUT_OF_BOUNDS)
            self.vessel_model.setZ(-1.2)
