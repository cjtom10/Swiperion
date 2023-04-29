import random

from direct.actor.Actor import Actor
from panda3d.ai import AICharacter, AIWorld
from panda3d.bullet import (BulletCylinderShape, BulletRigidBodyNode,
                            BulletWorld, ZUp)
from panda3d.core import (BitMask32, CollisionNode, CollisionSphere, NodePath,
                          Vec3)

CYLINDER_SHAPE = BulletCylinderShape(0.5, 2.4, ZUp)


class Vessel:
    def __init__(
        self,
        worldNP: NodePath,
        world: BulletWorld,
        aiWorld: AIWorld,
        player: NodePath,
        is_possessed=False,
    ) -> None:
        self.is_possessed = is_possessed

        self.body = worldNP.attachNewNode(BulletRigidBodyNode('Cylinder'))
        self.body.node().setMass(1.0)
        self.body.node().addShape(CYLINDER_SHAPE)
        self.body.setPos(
            random.randrange(-20, 20), random.randrange(30, 50), 3
        )
        self.body.setHpr(0, 0, 0)
        self.body.setCollideMask(BitMask32.allOn())
        world.attachRigidBody(self.body.node())

        model = Actor(
            'johnooi/johnooi.bam',
            {
                'idle': 'johnooi/johnooi_Idle.bam',
                'walk': 'johnooi/johnooi_walk.bam',
            },
        )
        model.loop('idle')
        model.reparentTo(self.body)
        model.setZ(-1.2)
        model.setScale(0.6)
        # TODO: could dynamically switch back to idle, but it will always be moving or about.coming
        model.loop('walk')

        self.hitbox = self.body.attachNewNode(CollisionNode('hit'))
        sphere = CollisionSphere(0, 0, 0, 1)
        self.hitbox.node().addSolid(sphere)

        self.aiWorld = aiWorld
        self.player = player
        self.aiChar = AICharacter(repr(self), self.body, 100, 0.5, 2)
        self.aiWorld.addAiChar(self.aiChar)
        self.aiBehaviors = self.aiChar.getAiBehaviors()

    def update(self):
        if self.is_possessed:
            self.aiBehaviors.pursue(self.player)
        else:
            self.aiBehaviors.wander()
