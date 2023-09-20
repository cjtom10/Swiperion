import math
import random

from direct.actor.Actor import Actor
from direct.interval.ActorInterval import ActorInterval, LerpAnimInterval
from direct.interval.IntervalGlobal import Func, Parallel, Sequence, Wait
from direct.interval.LerpInterval import *
from direct.showbase.ShowBase import ShowBase
from panda3d.ai import AICharacter, AIWorld
# from panda3d.bullet import (BulletCylinderShape, BulletRigidBodyNode,
#                             BulletWorld, ZUp)
# from panda3d.core import (BitMask32, CollisionNode, CollisionSphere, NodePath,
#                           Vec3)
from panda3d.bullet import *
from panda3d.core import *

CYLINDER_SHAPE = BulletCylinderShape(0.5, 2.4, ZUp)
CAPSULE_SHAPE = BulletCapsuleShape(0.5, 2.4, ZUp)

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

        # self.body = worldNP.attachNewNode(BulletRigidBodyNode('Cylinder'))
        controller = BulletCharacterControllerNode(CYLINDER_SHAPE, 1, 'npc')
        self.body = worldNP.attachNewNode(controller)
        # self.body.node().setMass(1.0)
        # self.body.node().addShape(CYLINDER_SHAPE)
        # self.body.node().addShape(CAPSULE_SHAPE)
        self.body.setPos(
            random.randrange(-20, 20), random.randrange(30, 50), 3
        )
        self.body.setHpr(0, 0, 0)
        self.body.setCollideMask(BitMask32.allOn())
        # self.body.setCollideMask(BitMask32.allOn())
        # world.attachRigidBody(self.body.node())
        world.attachCharacter(self.body.node())

        self.vessel_model = Actor(
            'models/johnooi.bam',
            {
                'idle': 'models/johnooi_Idle.bam',
                'walk': 'models/johnooi_walk.bam',
                'stationary': 'models/johnooi/johnooi_scared1.bam',
            },
        )
        self.vessel_model.setHpr(180, 0, 0)
        self.vessel_model.loop('idle')
        self.vessel_model.reparentTo(self.body)
        # self.vessel_model.setZ(-1.2)
        self.vessel_model.setScale(0.6)
        self.vessel_model.loop('walk')

        self.possessed_model = Actor(
            'possessed/possessed.bam',
            {
                'spawn': 'possessed/possessed_spawn.bam',
                'run': 'possessed/possessed_run.bam',
                'slash1': 'possessed/possessed_slash1.bam',
                'slash2': 'possessed/possessed_slash2.bam',
                'stab': 'possessed/possessed_stab.bam',
                'recoil': 'possessed/possessed_recoil1.bam',  # play this before deflected
                'deflected': 'possessed/possessed_deflected.bam',
                'death': 'possessed/possessed_death.bam',
                'stagger': 'possessed/possessed_stagger.bam',
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

        self.HP = 100
        # TODO placeholder hb, switch to self.HB
        # self.hitbox = self.possessed_model.attachNewNode(CollisionNode(f'{self.name}hitbox'))
        # sphere = CollisionSphere(0, 0, 2, 2)
        # self.hitbox.node().addSolid(sphere)

        # print(self.hitbox)

        ########  only attach during active frames of atrk anim
        sphere = CollisionSphere(0, 2, 0, 2)
        self.lclaw_hitbox = self.lclaw_model.attachNewNode(
            CollisionNode(f'{self.name}clawL')
        )
        # self.lclaw_hitbox.node().addSolid(sphere)
        self.rclaw_hitbox = self.rclaw_model.attachNewNode(
            CollisionNode(f'{self.name}clawR')
        )
        # self.rclaw_hitbox.node().addSolid(sphere)

        # TODO: rm, debug only to show hitbox
        # self.hitbox.show()
        self.atkHB = [self.rclaw_hitbox, self.lclaw_hitbox]

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

        self.vesselBehavior = random.randint(
            1, 2
        )  # 1= wander, 2 = idle/scared
        ### hitboxes AND ATtasck stuff] for when possessed

        self.SA = 0   # super armor count - increases with successive atx
        self.isHit = False
        self.currentSeq = None

        self.HB = []
        self.HBsetup(self.possessed_model, self.HB, True, self.name)

    def HBsetup(self, actor, HBlist, visible, name):
        """set up hitbox for taking damage"""
        # print(self.charM.listJoints())
        head = actor.expose_joint(None, 'modelRoot', 'head')
        chest = actor.expose_joint(None, 'modelRoot', 'chest')
        rightbicep = actor.expose_joint(None, 'modelRoot', 'bicep.R')
        rightforearm = actor.expose_joint(None, 'modelRoot', 'forarm.R')
        rightthigh = actor.expose_joint(None, 'modelRoot', 'femur.R')
        rightshin = actor.expose_joint(None, 'modelRoot', 'shin.R')
        leftbicep = actor.expose_joint(None, 'modelRoot', 'bicep.L')
        leftforearm = actor.expose_joint(None, 'modelRoot', 'forarm.L')
        leftthigh = actor.expose_joint(None, 'modelRoot', 'femur.L')
        leftshin = actor.expose_joint(None, 'modelRoot', 'shin.L')

        # print(self.head.getPos(render))
        headsphere = CollisionSphere(0, 0, 0, 0.1)
        chestsphere = CollisionSphere(0, 0.2, 0, 0.75)
        arm = CollisionCapsule((0, -0.2, 0), (0, 0.8, 0), 0.07)
        leg = CollisionCapsule((0, -0.38, 0), (0, 1, 0), 0.1)
        # forearm =  CollisionCapsule((0,-.2,0),(0,.8,0),0.07)
        # self.characterHitB = self.character.movementParent.attachNewNode(CollisionNode('character'))

        # self.characterHB = []

        # self.headHB = self.characterHitB.attachNewNode(CollisionNode('head'))
        # self.headHB.reparentTo(self.characterHitB)
        # self.headHB.node().addSolid(headHB)
        # self.headHB.show()
        # self.characterHB.append(self.headHB)
        # self.headHB.setCompass(self.head)
        # self.headHB.setPos(self.head, 0,0,7)
        # self.characterHitB.show()

        headHB = head.attachNewNode(CollisionNode(f'{name}head'))
        headHB.node().addSolid(headsphere)
        headHB.setZ(-0.2)
        # self.headHB.show()
        HBlist.append(headHB)
        # self.headHB.wrtReparentTo(self.characterHitB)

        chestHB = chest.attachNewNode(CollisionNode(f'{name}chest'))
        chestHB.node().addSolid(chestsphere)
        chestHB.setY(-0.2)
        # self.chestHB.show()
        HBlist.append(chestHB)
        # self.chestHB.reparentTo(self.characterHB)

        self.bicepR = rightbicep.attachNewNode(CollisionNode(f'{name}bicepr'))
        self.bicepR.node().addSolid(arm)
        # self.bicepR.show()
        HBlist.append(self.bicepR)

        self.forarmR = rightforearm.attachNewNode(
            CollisionNode(f'{name}forearmr')
        )
        self.forarmR.node().addSolid(arm)
        # self.forarmR.show()
        HBlist.append(self.forarmR)

        self.thighR = rightthigh.attachNewNode(CollisionNode(f'{name}thighr'))
        self.thighR.node().addSolid(leg)
        # self.thighR.show()
        HBlist.append(self.thighR)

        self.shinR = rightshin.attachNewNode(CollisionNode(f'{name}shinr'))
        self.shinR.node().addSolid(leg)
        # self.shinR.show()
        HBlist.append(self.shinR)

        self.bicepL = leftbicep.attachNewNode(CollisionNode(f'{name}bicepl'))
        self.bicepL.node().addSolid(arm)
        # self.bicepL.show()
        HBlist.append(self.bicepL)

        self.forarmL = leftforearm.attachNewNode(
            CollisionNode(f'{name}forearml')
        )
        self.forarmL.node().addSolid(arm)
        # self.forarmL.show()
        HBlist.append(self.forarmL)

        self.thighL = leftthigh.attachNewNode(CollisionNode(f'{name}thighl'))
        self.thighL.node().addSolid(leg)
        # self.thighL.show()
        HBlist.append(self.thighL)

        self.shinL = leftshin.attachNewNode(CollisionNode(f'{name}shinl'))
        self.shinL.node().addSolid(leg)
        # self.shinL.show()
        HBlist.append(self.shinL)

        if visible == True:
            for node in HBlist:
                node.show()

    def stagger(self):
        """plays staggered anim thru when enemy is hit and player superarmor is greter than itself"""
        for claw in self.atkHB:
            claw.node().clearSolids()

        self.isHit = True
        if self.is_playing_any('staggered'):
            return
        self.possessed_model.play('staggered')
        self.taskMgr.doMethodLater(
            self.possessed_model.getDuration('staggered'),
        )

        self.state = 'staggered'

    def deflected(self):
        for claw in self.atkHB:
            claw.node().clearSolids()

    def idle(self):
        self.aiBehaviors.pauseAi('pursue')
        if self.is_playing_any('idle'):
            return
        self.possessed_model.loop('idle')

        self.state = 'idle'

    def is_playing_any(self, *anims):
        current_anim = self.possessed_model.getCurrentAnim()
        return any(current_anim == anim for anim in anims)

    @property
    def d2p(self):
        player_pos = self.player.getPos(render)
        vessel_pos = self.possessed_model.getPos(render)
        return (player_pos - vessel_pos).length()

    def rotate_to_face_player(self):
        direction_to_player = (
            self.player.getPos() - self.possessed_model.getPos()
        )
        heading = math.atan2(
            direction_to_player.getY(), direction_to_player.getX()
        )
        self.possessed_model.setH(math.degrees(heading) + 180)

    def pursue_player(self, task=None):
        self.state = 'pursue'
        self.rotate_to_face_player()
        self.aiBehaviors.pursue(self.player)
        if self.possessed_model.getCurrentAnim() == 'run':
            return
        self.possessed_model.loop('run')
        self.aiBehaviors.resumeAi('pursue')

    # def pursue_player(self, task=None):
    #     self.state = 'pursue'
    #     if self.is_playing_any('run'):
    #         return
    #     self.aiBehaviors.pursue(self.player)

    #     self.possessed_model.loop('run')

    def strafe(self):
        self.state = 'strafe'
        self.aiBehaviors.pauseAi('pursue')

        choice = random.random()
        dir_to_player = self.player.getPos() - self.body.getPos()
        norm_dir = dir_to_player.normalized()
        strafe_distance = 0.3
        step_distance = 0.05

        if choice < 0.2:
            strafe_vector = LVector3(norm_dir.getZ(), -norm_dir.getX(), 0)
            self.body.setPos(
                self.body.getPos() + strafe_vector * strafe_distance
            )
        # elif 0.6 <= choice < 0.8:
        #     self.body.setPos(self.body.getPos() + norm_dir * step_distance)
        # else:
        #     self.body.setPos(self.body.getPos() - norm_dir * step_distance)
        self.rotate_to_face_player()

    def attack(self, task=None):
        # not using this anymore
        self.aiBehaviors.pauseAi('pursue')
        attack = random.choice(list(self.attack_methods.keys()))
        self.attack_methods[attack]()
        self.state = 'attack'

    def attack_anim(self, anim, aFramestart, aFrameend, finalframe, Hand):
        self.aiBehaviors.pauseAi('pursue')
        a1 = self.possessed_model.actorInterval(
            anim, startFrame=0, endFrame=aFramestart
        )

        a2 = self.possessed_model.actorInterval(
            anim, startFrame=aFramestart + 1, endFrame=aFrameend
        )
        animfin = self.possessed_model.actorInterval(
            anim, startFrame=aFrameend + 1, endFrame=finalframe
        )

        def attachHb():
            sphere = CollisionSphere(0, 0, 2, 2)
            # self.rclaw_hitbox.node().addSolid(sphere)
            Hand.node().addSolid(sphere)
            # self.lclaw_hitbox.node().addSolid(sphere)

        def detachHB():
            # self.rclaw_hitbox.node().clearSolids()
            # self.lclaw_hitbox.node().
            Hand.node().clearSolids()

        attach = Func(attachHb)
        detach = Func(detachHB)

        self.currentSeq = Sequence(a1, attach, a2, detach, animfin)
        self.currentSeq.start()

    def slash1(self):
        if self.state == 'slash1':
            return
        self.state = 'slash1'
        self.aiBehaviors.pauseAi('pursue')
        self.attack_anim(
            'slash1',
            aFramestart=10,
            aFrameend=20,
            finalframe=25,
            Hand=self.lclaw_hitbox,
        )
        self.taskMgr.doMethodLater(
            1,
            self.slash1_post,
            f'{self.name}_slash2_or_pursue',
        )

    def slash2(self):
        if self.state == 'slash2':
            return
        self.state = 'slash2'
        self.aiBehaviors.pauseAi('pursue')
        self.attack_anim(
            'slash2',
            aFramestart=5,
            aFrameend=15,
            finalframe=25,
            Hand=self.rclaw_hitbox,
        )
        self.taskMgr.doMethodLater(
            1,
            self.attack_post,
            f'{self.name}_attack_or_pursue',
        )

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
        self.slash2() if self.d2p < 1 else self.pursue_player()

    def attack_post(self, task=None):
        self.slash1() if self.d2p < 1 else self.pursue_player()

    def possessed_death(self):
        # possessed dies and vessel retuyrns, spirit spawns in place
        pass

    def vessel_wander(self):
        self.aiBehaviors.wander()
        # if self.is_playing_any('walk'):
        #     return
        if self.vessel_model.getCurrentAnim() == 'walk':
            return
        self.vessel_model.loop('walk')

    def vessel_stationary(self):
        # if self.is_playing_any('stationary'):
        #     return
        # print(self.vessel_model.getCurrentAnim())
        if self.vessel_model.getCurrentAnim() == 'stationary':

            return
        self.vessel_model.loop('stationary')

    def update(self, task=None):

        self.body.setP(0)
        self.body.setR(0)
        # self.body.setZ(render,1) #because mass is 0, otherwise they will phase thru geom

        if not self.is_possessed:
            # self.aiBehaviors.wander()
            self.state = 'notPosessed'
            update_vessel = {1: self.vessel_wander, 2: self.vessel_stationary}
            update_vessel[self.vesselBehavior]()
            return
        # print(self.name, 'STATE', self.state)
        # wait for staggered anim to finish
        if self.state == 'staggered':
            return

        # wait for attack to finish
        if self.state == 'attack':
            self.aiBehaviors.pauseAi('pursue')
            return

        if self.d2p < 2:
            self.slash1()
            self.attack()
        elif self.d2p <= 2.5:
            self.strafe()
        else:
            self.pursue_player()

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


class HealthBar(NodePath):
    def __init__(self, pos):
        NodePath.__init__(self, 'healthbar')

        # self.postureBar(pos = (-1,1,0.6, .8))

        self.setShaderAuto()
        cmfg = CardMaker('fg')
        # cmfg.setFrame(-1, 1, -0.1, 0.1)
        cmfg.setFrame(pos)
        self.fg = self.attachNewNode(cmfg.generate())

        cmbg = CardMaker('bg')
        # cmbg.setFrame(-1, 1, -0.1, 0.1)
        cmbg.setFrame(pos)
        self.bg = self.attachNewNode(cmbg.generate())
        self.bg.setPos(1, 0, 0)

        self.fg.setColor(1, 0.5, 0, 1)
        self.bg.setColor(0.5, 0.5, 0.5, 1)

        self.setHealth(1.0)  # , full = True)

    def setHealth(self, value):  # , full = False):
        # if value ==1:
        #         value =.999
        # i
        # f value ==0:
        #         value =.001
        offset = 1.0 - value

        self.fg.setScale(value, 1, 1)
        self.bg.setScale(offset, 1, 1)

        self.fg.setPos(-offset, 0, 0)
        self.bg.setPos(1 - offset, 0, 0)
