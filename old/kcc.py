from contextlib import ContextDecorator
from pyexpat import model
from panda3d.core import *
from panda3d.bullet import BulletCapsuleShape, BulletRigidBodyNode, BulletGhostNode, BulletSphereShape
from direct.actor.Actor import Actor
from direct.showbase.InputStateGlobal import inputState
from direct.task import Task
from direct.interval.LerpInterval import LerpPosInterval
from direct.interval.IntervalGlobal import *
import math



# from anims import Anims
# from attacks import Attacks

# core = Game()

class PandaBulletCharacterController(object):
    """
    The custom kinematic character controller for Panda3D, replacing the Bullet's default character controller and providing more stability and features.
    
    Features included:
        * Walking with penetration prevention
        * Jumping with active and passive jump limiter. Active means limiting the max jump height based on the distance to the "ceiling". Passive means falling automatically when a "ceiling" is hit.
        * Crouching with stand up limiter which prevents the character from standing up if inside a tunnel or other limited space
        * Slope limiter of arbitrary maximum slope values which may or may not affect the movement speed on slopes smaller than maximum
        * Stepping, supports walking steps up and down (prevents "floating" effect)
        * Flying support for no-clip, ladders, swimming or simply flying
        * Simplified state system. Makes double/multiple jumps impossible by default 
        * Callbacks for landing and standing up from crouch
    
    The controller is composed of a levitating capsule (allowing stepping), a kinematic body and numerous raycasts accounting for levitation and spacial awareness.
    The elements are set up automatically.
    """
    def __init__(self, world, parent, walkHeight, crouchHeight, stepHeight, radius, gravity=None):#model ,
        """
        World -- (BulletWorld) the Bullet world.
        Parent -- (NodePath) where to parent the KCC elements
        walkHeight -- (float) height of the whole controller when walking
        crouchHeight -- (float) height of the whole controller when crouching
        stepHeight -- (float) maximum step height the caracter can walk.
        radius -- (float) capsule radius
        gravity -- (float) gravity setting for the character controller, currently as float (gravity is always down). The KCC may sometimes need a different gravity setting then the rest of the world. If this is not given, the gravity is same as world's
        """
        #input for anims
        # inputState.watchWithModifiers('forward', 'w')
        # inputState.watchWithModifiers('left', 'a')
        # inputState.watchWithModifiers('reverse', 's')
        # inputState.watchWithModifiers('right', 'd')
        # inputState.watchWithModifiers('turnLeft', 'q')
        # inputState.watchWithModifiers('turnRight', 'e')
        
        self.__world = world
        self.__parent = parent
        self.__timeStep = 0
        self.__currentPos = Vec3(0, 0, 0)
        
        self.movementParent = self.__parent.attachNewNode("Movement Parent")
        

        self.__setup(walkHeight, crouchHeight, stepHeight, radius)
        self.__mapMethods()
        
        self.gravity = self.__world.getGravity().z if gravity is None else gravity
        self.setMaxSlope(50.0, True)
        self.setActiveJumpLimiter(True)
       
        # self.fsm = charstates.CharacterFSM(self.movementParent)
        self.movementState = "ground"
        self.movementStateFilter = {
            
            "ground": ["ground", 
                        "jumping",
                        "falling",
                        "dodging"],
            "vaulting": ["ground", 
                        "jumping",
                        "falling"],
                        # "dodging"],
            # "walking":[],
            # "running":[],
            # "airborne": ["jumping",
            #             "falling",
            #             "dodging"],
            "jumping": ["ground",
                        "falling",
                        # "jumping",
                        #"dodging",
                        "airdodge",
                        "land"],
            "falling": ["ground",
                        # "jumping",
                        #"dodging",
                        "airdodge",
                        "land","flying"],
            "landing": ["ground",],
            # "dodging": ["ground", "falling", "exitdodge"],
            "dodging": ["dodging", "exitdodge"],#,"attacking"],# "jumping"],
            "exitdodge": ["falling", "jumping", "ground"],#, "attacking"],
            "airdodge": ["airdodge","falling", "jumping","exitdodge"],
            "grinding": ["grinding", "jumping"],
            "wallgrab": ["jumping"],
            # "exitgrind": ["falling", "jumping", "ground"],
            # "attacking":[attacking, end attack]
            "attacking": ["groundattacking","jumping", "dodging","airdodge", "endaction"],
            "airattacking": ["airattacking", "jumping", "falling"],
            "endaction": ["falling", "jumping", "ground","dodging","airdodge"],
            #mech states
            "flying":["ground", "falling"],
            "mech" : [],
            "grappling": ["ground","jumping", "falling"]

        }
        self.airstates = ["falling", "jumping","airattacking", "airdodge", "wallgrab"]
        self.nonInputStates = ["wallgrab","vaulting","finisher"]#, "jumping"]
        # self.model = model
        self.d2wall=0
        # Prevent the KCC from moving when there's not enough room for it in the next frame
        # It doesn't work right now because I can't figure out how to add sliding. Sweep test could work, but it would cause problems with penetration testing and steps
        # That said, you probably won't need it, if you design your levels correctly
        self.predictFutureSpace = True
        self.futureSpacePredictionDistance = 10.0
        
        self.isCrouching = False
        self.isdodging = False
        self.isLanding = False
        
        # self.grindcenter = None
        self.isAttacking = False# isAttacking/isParrying  sets movement during tx and parries, and limits dodging/jumping during active frames
        self.isParrying=False
        self.deflecting = False
        self.airAttack =False
        self.HBframes = False

        self.perfectDodge = False
        # self.atack1 = False
        # self.attack2 = False
        # self.attack3 = False


        self.__fallTime = 0.0
        self.__fallStartPos = self.__currentPos.z
        self.__linearVelocity = Vec3(0, 0, 0)
        self.__headContact = None
        self.__footContact = None
        self.__enabledCrouch = False
        
        self.__standUpCallback = [None, [], {}]
        self.__fallCallback = [None, [], {}]

        # self.setFallCallback(method=self.fallback)
        # self.__fallCallback[0](self.__fallStartPos, *self.__fallCallback[1], **self.__fallCallback[2])
        ##### MODEL + ANIMS
        # self.char = loader.loadModel('../models/guy.bam')
        self.grappleVec = Vec3
        self.grappleGround = False
        self.preGrapple = True
        self.grappleEnemyContact = False

        # self.health = .99
        self.char = model
        
        # # Actor('../models/player/char.bam',{
        #                   'idle' : '../models/player/char_idle.bam',
        #                   'run' : '../models/player/char_running.bam',
        #                   'walk' : '../models/player/char_walk.bam',
        #                   'sprint' : '../models/player/char_run.001.bam',
        #                   'attackwalk' : '../models/player/char_atackwalk.bam',
        #                   'jump' : '../models/player/char_Jump.bam',
        #                   'jump2' : '../models/player/char_Jump2.bam',
        #                   'falling' : '../models/player/char_falling.bam',
        #                   'land' : '../models/player/char_land2.001.bam',
        #                   'shortland' : '../models/player/char_shortland.bam',
        #                   'dodge' : '../models/player/char_dodge.bam',
        #                   'airdodgeL' : '../models/player/char_airdodgeLeft.bam',
        #                   'airdodgeR' : '../models/player/char_airdodgeRight.bam',
        #                   'airdodgeF' : '../models/player/char_airdodgeForward.bam',
        #                   'airdodgeB' : '../models/player/char_airdodgeBack.bam',
        #                   'kick1' : '../models/player/char_slashkick1.bam',
        #                   'kick2' : '../models/player/char_slashkick2.bam',
        #                   'kick3' : '../models/player/char_slashkick3.bam',
        #                   'stab1' : '../models/player/char_stab1.bam',
        #                   'stab2' : '../models/player/char_stab2.bam',
        #                   'stab3' : '../models/player/char_stab3.bam',
        #                    'pausekick' : '../models/player/char_kick3.bam',
        #                    'smash' : '../models/player/char_smash.bam',
        #                 #    'parry' : '../models/player/char_parry.bam',
        #                  'parry' : '../models/player/char_deflect.bam',
        #                  'airParry' : '../models/player/char_airdeflect.bam',
        #                  'recoil1' : '../models/player/char_recoil01.bam',
        #                  'recoil2' : '../models/player/char_recoil2.bam',
        #                   'grind' : '../models/player/char_grind.bam',
        #                   'vaultend' : '../models/player/char_vaultend.bam',
        #                   'vaultup' : '../models/player/char_vaultup.bam',
        #                   'wallgrabL' : '../models/player/char_wallgrabL.bam',
        #                   'wallgrabR' : '../models/player/char_wallgrabR.bam',
        #                   'wallrunR' : '../models/player/char_wallrunR.bam',
        #                   'wallrunL' : '../models/player/char_wallrunL.bam',
        #                   'takehit' : '../models/player/char_takedamage1.bam',
        #                   'finisher' : '../models/player/char_finisher.bam',
        #                   'die' : '../models/player/char_die.bam',
        #                   'grappleGround' : '../models/player/char_grappleGround.bam',
        #                   'grappleAir' : '../models/player/char_grappleAir.bam',
        #                   'perched' :  '../models/player/char_perched.bam',
        #                   'perchJumpR' :  '../models/player/char_perchjumpR.bam',
        #                   'perchJumpL' :  '../models/player/char_perchjumpL.bam',
        #                   'perchJumpF' :  '../models/player/char_perchjumpF.bam',
        #                   'perchJumpB' :  '../models/player/char_perchjumpB.bam',
        #                    'fallingF' :  '../models/player/char_fallingF.bam',
        #                    'fallingL' :  '../models/player/char_fallingL.bam',
        #                    'fallingR' :  '../models/player/char_fallingR.bam',
        #                 #   'airdodgeR' : '../models/char_airdodgeR.bam'                          
        #                   })
        # self.mech = Actor('../models/player/mech.bam', {
        #                     'idle': '../models/player/mech_idle.bam',
        #                     'parry': '../models/player/mech_deflect.bam',
        #                     'ground': '../models/player/mech_ground.bam',
        #                     'fly': '../models/player/mech_flying.bam',
        #                     'slash1': '../models/player/mech_slash1.bam',
        #                     'slash2': '../models/player/mech_slash2.bam',
        #                     'slash3': '../models/player/mech_slash3.bam',
        #                     'stab1': '../models/player/mech_stab1.bam',
        #                     'stab2': '../models/player/mech_stab2.bam',
        #                     'stab3': '../models/player/mech_stab3.bam',
        # })
        # self.char = self.movementParent
        #self.char switches depending on if mech or on foot

        # self.char.reparentTo(self.movementParent)
        self.char = NodePath('char')
        ##mech or onfoot? onfoot initialized here
        self.state = 'OF'


        self.HB=[]
#########FOR VAULTING      )
        self.enableVaulting = False
        self.isVaulting = False
        self.vaultcheckNode = self.char.attachNewNode('vaultcheck')
        self.vaultcheckNode.setPos(self.movementParent, (0,1.5,4.5))
        self.vaultcheckNode2 = self.char.attachNewNode('vault check bopttom')
        self.vaultcheckNode2.setPos(self.movementParent, (0,1.5,1))

        self.uwu = NodePath('uwu')#loader.loadModel('../models/sword.glb')
        self.jumpdirNode = NodePath('jumpdir')#loader.loadModel('../models/sword.glb')
        self.uwu.reparentTo(self.vaultcheckNode)
        self.uwu.instanceTo(self.vaultcheckNode2)
#########FOR WALL JUMP/ WALL RUN
        self.wallray = render.attachNewNode('wallcontact raycheck')
        self.wallray.setY(self.movementParent, 3)
        self.wallray.setH(90)
        self.canWallGrab = True
        self.WGAngle = None

        self.sweepR = self.char.attachNewNode('sweepR')
        self.sweepR.setPos(2,1.5,1)
        self.sweepL = self.char.attachNewNode('sweepL')
        self.sweepL.setPos(-2,1.5,1)
        # self.wrp1 = self.wallray.attachNewNode('p1')
        # self.wrp1.setY(-1)
        # self.wrp2 = self.wallray.attachNewNode('p2')
        # self.wrp2.setY(1)
        # self.uwu.instanceTo(self.wrp1)
        # self.uwu.instanceTo(self.wrp2)
    
        self.wallContact = False
        self.wallJump = False
        self.nearWall = False
        self.uwu.instanceTo(self.wallray)
        self.jumpx=0
        self.jumpy=0
        # self.wallRunDir = 0
        # self.wallgrabanim = 
        self.wallRunVec = Vec3(0,0,0)
        self.wallspeed = 0
        self.wallRun = [None, None, Vec3(0,0,0), False, None]#, True]#wallrun[0] is the angle, 2 is the anim, 3 is the speed to be applied, 3 is if you are wallrunning or not
       #  determines if you can grab, to prevent re grabbing from a timer end
       #4 is the state you are in, grabbing or running
# 4        # self.vaultTask = None
        
        self.vaulting=False
        self.ledgeZ=None
        self.ledgegrab = None
        self.vaultseq = None
        self.vaultvec =None
############
        #movement tokens for jump/ evades
        self.movepoints = 4 ##CONFIG
        self.movetimer = False
        self.dodgedir =None
        self.jumpdir =None
        self.jumpdirNode = NodePath('jumpdirnorde')#loader.loadModel('../models/sword.glb')
        self.jumpdirNode.reparentTo(render)
        self.vec = None#vec becomes jumpdir

        self.dodgetask = None
      
        self.grindvec = Vec3(0,0,0)
        
        self.queueJump = False

        # self.feetonground()
#########for smash attack duh
        self.smash1=False
        self.smash2=False
        self.smashtask = None
        self.smashonground = False

        self.mechVec = Vec3
        self.ascending = False
        # Anims.__init__(self)
    def setCollideMask(self, *args):
        self.__walkCapsuleNP.setCollideMask(*args)
        self.__crouchCapsuleNP.setCollideMask(*args)
    def fallback(start_pos):
        print('land')

    def setFallCallback(self, method, args=[], kwargs={}):
        """
        Callback called when the character falls on thge ground.
        
        The position where falling started is passed as the first argument, the additional argument and keyword arguments follow.
        """
        self.__fallCallback = [method, args, kwargs]
    
    def setStandUpCallback(self, method, args=[], kwargs={}):
        """
        Callback called when the character stands up from crouch. This is needed because standing up might be prevented by spacial awareness. 
        """
        self.__standUpCallback = [method, args, kwargs]
    
    def setMaxSlope(self, degs, affectSpeed):
        """
        degs -- (float) maximum slope in degrees. 0, False or None means don't limit slope.
        affectSpeed -- (bool) if True, the character will walk slower up slopes
        
        Both options are independent.
        
        By default, affectSpeed is enabled and maximum slope is 50 deg.
        """
        if not degs:
            self.minSlopeDot = None
            return
        self.minSlopeDot = round(math.cos(math.radians(degs)), 2)
        
        self.__slopeAffectsSpeed = affectSpeed
    
    def setActiveJumpLimiter(self, val):
        """
        Enable or disable the active jump limiter, which is the mechanism that changes the maksimum jump height based on the space available above the character's head.
        """
        self.__intelligentJump = val
    
    def startCrouch(self):
        self.isCrouching = True
        self.__enabledCrouch = True
        
        self.capsule = self.__crouchCapsule
        self.capsuleNP = self.__crouchCapsuleNP
        
        self.__capsuleH, self.__levitation, self.__capsuleR, self.__h = self.__crouchCapsuleH, self.__crouchLevitation, self.__crouchCapsuleR, self.__crouchH
        
        self.__world.removeRigidBody(self.__walkCapsuleNP.node())
        self.__world.attachRigidBody(self.__crouchCapsuleNP.node())
        
        self.__capsuleOffset = self.__capsuleH * 0.5 + self.__levitation
        self.__footDistance = self.__capsuleOffset + self.__levitation

    
    def stopCrouch(self):
        """
        Note that spacial awareness may prevent the character from standing up immediately, which is what you usually want. Use stand up callback to know when the character stands up.
        """
        self.__enabledCrouch = False
    
    def isOnGround(self):
        """
        Check if the character is on ground. You may also check if the movementState variable is set to 'ground'
        """
        if self.__footContact is None:
            return False
        elif self.movementState == "ground":
            elevation = self.__currentPos.z - self.__footContact[0].z
            return (elevation <= self.__levitation + 0.02)
   
        
        else:
            return self.__currentPos <= self.__footContact[0]

        
    
    def startJump(self, maxHeight=1.5, state='jumping', walljump = False):
        """
        max height is 3.0 by default. Probably too much for most uses.
        """
        # if state == 'vaulting':
            # self.jumpdir = render.getRelativeVector(self.char, Vec3(0, 10, 0))
            # self.jumpdir = self.char.getQuat().getForward() * 10
        # if state == "grappling"
        # print('vaukt hums')
        self.__currentPos = self.movementParent.getPos()
        self.__jump(maxHeight, state, walljump)
    
    # def queueJump(self, task):
    #     # self.__jump(5)
    #     print('yahoo')
    #     #wait till dodge is over then jump
    #     return task.done

    def startFly(self):
        self.movementState = 'flying'
    
    def stopFly(self):
        """
        Stop flying and start falling
        """
        self.__fall()
    
    def setAngularMovement(self, omega):
        self.movementParent.setH(self.movementParent, omega * self.__timeStep)
    
    def setLinearMovement(self, speed, *args):
        self.__linearVelocity = speed
    
    def update(self, timestep=None,):
        """
        Update method. Call this around doPhysics.
        """
        # print('wall contact', self.wallContact)
        # print('mvtstate', self.movementState)
        # print(self.__footContact, self.isOnGround())
        # if self.__footContact!=None: 
        #     if self.isOnGround()==True:
        #         print('waaaaa')
        # print('fallcallback',self.__fallCallback)
        # self.feetonground()
        # if self.__footContact is not None:
        
        # print("mvtstate",self.movementState,"footcontact",self.__footContact)#,"anim:",self.char.getCurrentAnim(),"mvtstate:", self.movementState)
        # print(self.__currentPos.z)
        # print("chaar", self.char.getZ(render))

        if self.movementState in self.airstates:
           self.jumpdir= self.movementParent.getRelativeVector(self.jumpdirNode, (0,10,0))#need 2 divide last thing in half
           print('jumpdir', self.jumpdir) 
            
        #     self.jumpdir = self.updatejumpDir(self.vec)
        #     print('airstates', self.jumpdir,self.vec)# self.movementParent.getRelativeVector(self.char, (0,10,0)))
        # vec = self.char.getQuat().getForward() * 10)
        processStates = {
            "ground": self.__processGround,
            # "Idle": self.isIdle,
            "jumping": self.__processJumping,
            "falling": self.__processFalling,
            # "landing": self.processLand,
            "dodging": self.processdodge,
            "airdodge": self.processdodge,
            "flying": self.__processFlying,
            "walking": self.__processGround,
            # "exitdodge": self.exitdodge,
            # "grinding": self.processGrind,
            "finisher": self.processFinisher,
            # "exitgrind": self.exitGrind,
            "attacking": self.processAttack,
            "endaction": self.endaction,
            "vaulting": self.__processJumping,
            "wallgrab": self.processWallGrab,
            "grappling": self.processGrapple
            # "stunned": self.processFinisher,
            # "mech": self.processMech,
            # \\"running": 
        }
        processStatesMech = {
              "mech": self.processMech,
              "ground": self.__processGround,
               "attacking": self.processAttack,
            #   "jumpn"
                "flying": self.__processFlying,
              "falling": self.__processFalling,
              "dodging": self.processdodge,
              "endaction": self.endaction,
        }
        # print(self.movementState)
       
        if timestep is None:    
            self.__timeStep = globalClock.getDt()
        else:
            self.__timeStep = timestep
        
        self.__updateFootContact()
        self.__updateHeadContact()
        
        # if self.state =='OF':
        processStates[self.movementState]()
        self.wallcheck()

        # if self.state == 'mech':
        #     processStatesMech[self.movementState]()
            # print('mechstate',self.movementState)
        # print(self.state)
         
        self.__applyLinearVelocity()
        self.__preventPenetration()
        
        self.__updateCapsule()
        
        
        # print(self.char.getH())
        # if self.isCrouching and not self.__enabledCrouch:
        #     self.__standUp()
    
        if self.movementState!= "dodging" or "airdodge" and self.dodgetask!=None:
            # taskMgr.remove('dodge)
            self.dodgetask= None

        self.d2wall = (self.wallray.getPos(render) - self.movementParent.getPos(render)).length()
    def processMech(self):
        self.setLinearMovement(self.mechVec)
        print('mech vec',self.mechVec)
        # self.mechVec.z = -3
        #add floor contact, downward vec
    # def mpHCheck(self, initH):
    #     """checkk rotation diff if airbone"""
    #     print('inith',initH,'currenth',self.movementParent.getH(render))
    def setJumpdir(self, dir):
       # calls everytimeu enter air state: node moves to MP, points in way of jumpDir, reparent to render there is ur jump dir
        self.jumpdirNode.setPos(self.movementParent.getPos(render))
        vec = self.jumpdir
        angle = math.atan2(-vec.x,vec.y)
        print(angle)
        self.jumpdirNode.setH(math.degrees(angle))

        print('rel vec jumpdiur',self.movementParent.getRelativeVector(self.jumpdirNode, (0,10,0)))

        # self.jumpdirNode.setH()
    def updatejumpDir(self,jd):
        """when airborne: jumpdir should always be constant, ignoring movement parent  rotation"""
        # vec = self.movementParent.getRelativeVector(render, jd)
            # jd is either str8 or rel to mvt parent
        # vec = self.char.getQuat().getForward() * 10
        # vec = self.movementParent.getRelativeVector(self.char, jd)
        vec = jd #works for facing forward
        # vec = render.getRelativeVector(self.movementParent, jd)
        return vec
    def processFinisher(self):
        self.__currentPos = self.movementParent.getPos()
        self.setLinearMovement(0)
        return
    def __land(self, smash = False):#task
        # self.wallRun[4] = True
        if self.canWallGrab == False:
            self.canWallGrab=True
        self.movementState = "ground"
        if self.movepoints!=3:
            self.movepoints=3
        falldist = abs(self.__fallStartPos -self.__currentPos.z)
        
        # print('falldist:',falldist)
        if falldist < 1:
            print('too low to land')
            return
        self.isLanding = True
        # if(self.char.getCurrentAnim()!="land"):#$ and falldist > 5:
            
        #     self.char.setPlayRate(1, "land")
        #     self.char.play("land")
        if smash == True:
            print('SUUUH MASSH!s')
            self.smashonground = True
        # else:
        #     self.char.setPlayRate(1, "shortland")
        #     self.char.play("shortland")     
        # self.__fallCallback[0](self.__fallStartPos, *self.__fallCallback[1], **self.__fallCallback[2])    
      
        # self.isLanding = True
        # if task.time < 0.1:
        #     self.isLanding = True
        #     return Task.cont
        # else:
        #     self.movementState = "ground"
        #     self.isLanding = False
        #     return Task.done

    # def processLand(self): 
    #     if "landing" not in self.movementStateFilter[self.movementState]:
    #         return
    #     self.movementState = "landing"
    
    def __fall(self):
        if "falling" not in self.movementStateFilter[self.movementState]:
            return
        # self.setFallCallback(None)
        
        
        
        self.__fallStartPos = self.__currentPos.z
        self.fallDelta = 0.0
        self.__fallTime = 0.0

        
        #     hit = ray.getHitPos().z
        #     dis = pFrom.z-hit
        #     # print(dis)
        #     if abs(dis)<1:
        #         self.movementState="ground"
        #     else:
        self.movementState = "falling"
        ######################################################
        # sorted_hits = sorted(result.getHits(), key = lambda hit: (pFrom - hit.getHitPos()).length())
        
      
        
    def resetmovepoints(self, task):
        #Cooldown for air dodge and jump
        
        # movepoints = self.movepoints
        # self.movetimer = True

        # if task.time < 3:
        #     return Task.cont
        # else:
        #     self.movepoints = 3
        #     print('reset! movepoints')
        #     self.movetimer = False
            # return Task.done
        pass
    def __jump(self, maxZ = 3.0, mvtstate = 'jumping', walljump =False):
        print('current jump pos', self.__currentPos)
        if "jumping" not in self.movementStateFilter[self.movementState]: #and self.isVaulting == False:
            print(self.movementState,'nonononononononon')
            return
        # if mvtstate =="jumping" and walljump==False:
        #     if self.movepoints == 0:
        #         return
        #     if self.movepoints!=0:
        #         self.movepoints -=1

        # if self.movementState != 'grinding':
        #     self.__world.removeRigidBody(self.__walkCapsuleNP.node())
        
        maxZ += self.__currentPos.z
        
        if self.__intelligentJump and self.__headContact is not None and self.__headContact[0].z < maxZ + self.__h:
            maxZ = self.__headContact[0].z - self.__h * 1.2
        
        maxZ = round(maxZ, 2)
        
        self.jumpStartPos = self.__currentPos.z
        self.jumpTime = 0.0
        
        bsq = -6.0 * self.gravity * (maxZ - self.jumpStartPos)
        try:
            b = math.sqrt(bsq)
        except:
            return
        self.jumpSpeed = b
        self.jumpMaxHeight = maxZ
  

        
        self.movementState = mvtstate


        #add in grind momentum

    def processGrind(self):
        self.jumpdir = self.grindvec

        self.__currentPos = self.movementParent.getPos()
    def processGrapple(self):
        self.__currentPos = self.movementParent.getPos()
        if self.preGrapple == True or self.grappleEnemyContact==True:
            self.setLinearMovement(0) 
            return
        if self.grappleGround==True:
            self.grappleVec  =  self.char.getQuat().getForward() * 50  
            # print('dodge  dir',self.dodgedir)
            self.setLinearMovement(self.grappleVec) 
            # print('grappling ground')
            self.__currentPos.z = self.__footContact[0].z
            # self.__processGround()
            # return
        # self.setLinearMovement(self.grappleVec * 5)
        #self.char.getQuat().getForward()

    def processWallGrab(self):
        """Snaps player to closest adjascent wall angle. timer forsimply grabbing the wall (and not wall runing)"""
        # print(self.__footContact)
        # print(self.d2wall)
        # if self.wallContact == False:
        #     self.movementState = 'endaction'
        #     return
        if self.__footContact is not None:
            self.__land()
            return
        dir = self.char.getH(self.wallray)
        self.wallRun[0] = self.wallray.getH(render)
        if dir <0:
            self.wallRun[0] -= 90
            self.wallRun[1] = 'right'
        elif dir>0:
            
            self.wallRun[0]+=90# 'footcontact', self.__footContact)
            self.wallRun[1] = 'left'
            # self.sweepR.setPos(-2,0,1)
        #Wall grab vs wall run states
        # self.wallRun[2] += self.wallRunVec#add run input
        # WRspeed = render.getRelativeVector(self.char, self.wallRun[2])# make relative to render
        WRspeed =self.wallRun[2] #+ (self.char.getQuat().getForward() *self.wallspeed)
        print('wrspeed', WRspeed)
        # if self.wallRun[4] == 'wallrunning':
        #     self.wallray.wrtReparentTo(self.char)
        # print(self.wallRun[2])
        # print(WRspeed)
        self.setLinearMovement(WRspeed)
        #Both states have -z movement
        #wall grab has timer

        #if run, self.wallrun3 = true
        
        return

    # def testexitgrind(self):
    #     taskMgr.add(self.exitGrind)    

    # def exitGrind(self, task):
    #     # self.__jump()
    #     # if not self.isOnGround():
    #     #     self.__fall()
    #     # else:
    #     #     self.movementState = "ground"
        
    #     if task.time < 3:
    #         self.setLinearMovement(self.dodgedir)
    #         self.dodgedir *= .3
    #         return task.cont

    #     return task.done

    # def startdodge(self):
    #     self.char.stop()
    #     if self.char.getCurrentAnim()!="dodge":
    #         self.char.disable_blend()
    #         self.char.play("dodge")
    #     self.isdodging=True
    #     self.movementState = "dodging"
    #     if self.dodgetask == None:
    #         self.dodgetask = taskMgr.add(self.dodge,name= 'dodge')
    #     print('start dodge')

    def startAtkdodge(self):
        if self.dodgetask == None:
                self.dodgetask = taskMgr.add(self.dodge,name= 'dodge')

        
    def startairdodge(self):
        print('aiordodge')
        # if self.movepoints ==0:
        #     return
        # self.char.stop()
        # if self.char.getCurrentAnim()!="airdodgeF":
        #     self.char.play("airdodgeF")
        # self.isdodging=True
        # self.movementState = "dodging"
        # if self.dodgetask == None:
        #     self.dodgetask = taskMgr.add(self.dodge, name= 'dodge')
    
        if self.movepoints!=0:
            self.movepoints -=1

    # def dodge(self, task):
    #     if "dodging" not in self.movementStateFilter[self.movementState]:
    #         print('not in mvt state')
    #         return
    #     # elif self.movepoints == 0:
    #     #     return
    #     # self.movementState = "dodging"
    #     # if task.time < 0.5:
    #     # print('dodgey dodgey')
    #     if self.char.getCurrentFrame()==None:
    #         print('ende by way of non')
    #         # self.movementState = "exitdodge"
    #         return Task.done
    #     if self.char.getCurrentFrame() < 15:# NEED TO ACCOUNT FOR NONETYPE FR<AE# and self.isAttacking!=True:
    #         # print('dodge!')
    #         self.movementState = "dodging"
    #         self.isdodging = True
    #         # self.remainingdodge = task.time
    #         # print(self.dodgetime)
    #         return Task.cont
    #     if self.isAttacking==True:
    #         self.isdodging = False
    #         # print('exit dodge now')
    #         self.movementState = "exitdodge"
            
    #         return Task.done
    #     else:
    #         self.isdodging = False
    #         # print('exit dodge now')
    #         self.movementState = "exitdodge"
          

    #         return Task.done
    def airdodge(self, task):
        if "airdodge" not in self.movementStateFilter[self.movementState]:
            return
        # elif self.movepoints ==0:
        #     return
        # self.movementState = "dodging"
        # if task.time < 0.5:# USE FRAME INSTEAD
        if self.char.getCurrentFrame()==None:
            return Task.done
        if self.char.getCurrentFrame() < 8:
            self.movementState = "airdodge"
            self.isdodging = True
            return Task.cont
    
        else:
            self.isdodging = False
            # print('exit dodge now')
            self.movementState = "exitdodge"

            return Task.done

 
    def processdodge(self):
        # self.dodgedir *= x # add x bro
        # print('dodging')
        self.isdodging=True
        if self.__footContact is not None:
                self.__currentPos.z = self.__footContact[0].z

        if self.state == 'OF':
            # if self.__footContact is not None:
            #     self.__currentPos.z = self.__footContact[0].z


            if self.dodgedir == None:
                self.dodgedir = self.movementParent.getRelativeVector(self.char,Vec3(0,20,0))
                # self.dodgedir = self.char.getQuat().getForward() * 20
                print('dodgedir', self.dodgedir)
            # print('dodge  dir',self.dodgedir)
            self.setLinearMovement(self.dodgedir) 

            self.jumpdir = None
        if self.state =='mech':
            if self.dodgedir == None:
                self.dodgedir =  self.mech.getQuat().getForward() * 20
            print('dodge mech')
            self.setLinearMovement(self.mechVec * 3 ) 

    # def exitdodge(self):
    #     # if "exitdodge" not in self.movementStateFilter[self.movementState]:
    #     #     return
    #     taskMgr.remove('dodge')
    #     self.dodgetask= None
    #     if self.queueJump == True:
    #         self.startJump(5)
    #         self.__jump
    #         self.queueJump = False

    #     if not self.isOnGround():
    #         self.__fall()
    #     else:
    #         self.movementState = "ground"

    def endaction(self):
        """buffer state for exiting attack/parry/vault etc"""
        # print('state end action')
        # if "exitdodge" not in self.movementStateFilter[self.movementState]:
        #     return
        # if self.queueJump == True:
        #     self.startJump(5)
        #     self.__jump
        #     self.queueJump = False
        self.isdodging = False
        self.isVaulting = False
        print('end act8ionnnn')
        self.__currentPos = self.movementParent.getPos()
        if self.state == "OF":
            if not self.isOnGround() and self.__footContact==None:
                self.__fall()
            else:
                self.movementState = "ground"        
        if self.state == "mech":
            self.movementState = "flying"

    # def startattack(self):
    #     taskMgr.add(self.attacking)

    
    # def attacking(self, task):
    #     if task.time <1:
    #     # if self.isAttacking:
    #         self.movementState = "attacking"
    #         return Task.cont
    
    #     else:
    #         if self.attack2 == False:
    #             self.movementState = "exitdodge"
    #             self.jumpdir = Vec3(0,0,0)

    #             return Task.done
    def processAttack(self): ### TO DO : pass arguments here to account for atx with movement
        # print('attacking,', self.airAttack)
        # print(self.isOnGround())
        # self.__world.removeRigidBody(self.__walkCapsuleNP.node())
        if self.__footContact and self.__currentPos.z - 0.1 < self.__footContact[0].z and self.__linearVelocity.z < 0.0:
            self.__currentPos.z = self.__footContact[0].z
            self.__linearVelocity.z = 0.0
        atkVec =Vec3(0,0,0)
        if self.isParrying ==True and self.isAttacking==True: #no mvt for parries
            # if self.airParry==True:
            #     atkVec= -2
            # else:    
                atkVec = 0
                # print('parry')
        if self.airAttack == False:
            if self.isParrying ==True:
                atkVec = 0
                # print('parry')
            # print(self.isAttacking)
            # if not self.isOnGround:
            #     atkVec = self.char.getQuat().getForward() * 4
            #     atkVec.z +=-10
            #     print('airattack')
            #     # self.__fall()
            elif self.isAttacking == True: #and self.isParrying ==False:
                # print(atkVec)
                if self.state == "OF":
                    # atkVec = self.char.getQuat().getForward() * 2
                    atkVec=self.movementParent.getRelativeVector(self.char,Vec3(0,5,0))
                if self.state == "mech":
                    atkVec = self.__crouchCapsuleNP.getQuat().getForward() * 15
                    # self.mech.setH(self.movementParent, 0)
                # print('attackvec', )
            # print(atkVec)
            self.setLinearMovement(atkVec)

        if self.airAttack ==True: #and self.isOnGround == False:
                # return-use task instead
            #     if self.isParrying ==True:
            #         atkVec = 0
            #         print('parry')
            # # if self.isOnGround == False:
            #     print('air attaclk!')
            #     # atkVec.z +=-10
            #     atkVec =(0,0,-30)
            #     self.setLinearMovement(atkVec)
            #     if self.isOnGround() ==True:
            #         self.movementState ="endaction"
            #         self.airAttack = False
            #         self.__land()
            # pFrom = Vec3(0,0,self.__fallStartPos)
            # pTo = Vec3(0,0,-3)
            # ray = self.__world.rayTestClosest(pFrom, pTo)
            # if ray.hasHit():
            #     print('too close to ground')
            #     # self.movementState = 'endaction'
            #     return
            self.doSmashattack()
            # if self.smashtask ==None:
                # self.smashtask = taskMgr.add(self.doSmashattack)

            # taskMgr.add(doSmashattack)
        # if self.isAttacking == False:
        #     self.movementState == "endaction"
    def doSmashattack(self):
        self.movementState = "attacking" 
        self.isAttacking = True
        # print(self.isOnGround())
        if self.isOnGround() == False:
        # if self.__footContact == None:
            #placeholder, combine this with general "attacking state "
            if  self.smash1 == True:
                self.setLinearMovement((0,0,-2))
                print('in air')
                return #task.cont
            # else:
            if self.smash1 ==False:
                print('smashing')
                atkVec =(0,0,-30)
                self.setLinearMovement(atkVec)
                return #task.cont
        if self.isOnGround() ==True:
        # if self.__footContact!=None:
            print('endsmash')
            self.movementState ="endaction"
            self.airAttack = False
            self.smash1 = False
            self.smashtask = None
            self.isAttacking = False
            self.__land(smash=True)
            return #task.done          

    def wallcheck(self):
        """check for vault up FIRST then check for wallgrab"""
        mask = BitMask32.bit(0)
        pfrom=Point3(self.vaultcheckNode.getPos(render))
        pto=Point3(self.vaultcheckNode2.getPos(render))
        ledgecontact = self.__world.rayTestClosest(pfrom, pto, mask)
        # print('relative pos', self.wallray.getPos(self.movementParent))
        self.wallContact=False
        
        # print(self.wallray.getH())
        self.wallray.lookAt(self.movementParent)
        diff = self.wallray.getPos(render)- self.movementParent.getPos(render)
        # print(self.movementParent.getH(render), diff)
        charF = render.getRelativeVector(self.movementParent, Vec3(0,1,0))
        hF = render.getRelativeVector(self.wallray, Vec3(0,1,0))
        # print(charF, hF)
        # print(charF, diff)
        angle = charF.angleDeg(diff)
        # print(angle, ' charH', self.movementParent.getH(render), 'wallcheckH', self.wallray.getH(render)) 
        # print(angle)
        
        char = self.__walkCapsuleNP.node()
        wallcontact = self.__world.contactTest(char, mask)
        # wallContactNormal = self.__world.rayTestClosest(self.movementParent.getPos(render), self.wallray.getPos(render), mask).getHitNormal()
        # print('wallcontact normal', wallContactNormal)
        side = self.sweepL
        #initiate wallrun with contact, then use sweep to see if you are still near wall
        def sweep():# pass in argument for left/right side
            """sweep to determine proximity to wall for wallgrab"""
            fr = TransformState.makePos(self.sweepR.getPos(render))
            to = TransformState.makePos(self.sweepL.getPos(render))
            # print(self.sweepR.getPos())
            shape = BulletSphereShape(0.5)
            penetration = 0.0

            result = self.__world.sweepTestClosest(shape, fr, to, mask)
            # print(result.hasHit())
            if result.hasHit():
                # print('near wall')
                # print(result.getNode().name)
                # self.wallContact = True
                self.nearWall = True
            else:
                # print('not near wall')
                self.nearWall = False
        # sweep()
        if self.movementState in self.airstates:
            for contact in wallcontact.getContacts():
                if contact.getNode1().name == 'input_model_tri_mesh':
                    if self.enableVaulting==False:
                        self.wallContact = True
                        mpoint = contact.getManifoldPoint()
                        # print(mpoint.getPositionWorldOnA())
                        d=mpoint.getPositionWorldOnA()
                        # self.diss = (d-self.movementParent.getPos()).length()
                        # print(dis) # stay in wallrun if close enough
                        # print('difference,', diff, 'charH', self.char.getH(render))
                        # print(self.char.getH(render)) #- (self.movementParent.getPos())
                        # self.d2wall = (self.wallray.getPos(render) - self.movementParent.getPos(render)).length()
                        self.wallray.setPos(render, d)
            
                        self.wallray.setZ(self.movementParent, 0)
                        
                        # self.wallray.wrtReparentTo(self.movementParent)
                       
                        # print(mpoint.getAppliedImpulse())

                        # print(mpoint.getLocalPointA()),# self.char.getPos(render))
                        # print(mpoint.getLocalPointB())
                        # self.jumpx = (mpoint.getPositionWorldOnA().x-self.char.getX(render))  * 10
                        # self.jumpy = (mpoint.getPositionWorldOnA().y-self.char.getY(render) ) * 10
                        self.jumpx = (mpoint.getLocalPointA().x) * -20
                        self.jumpy = (mpoint.getLocalPointA().y) * -20
            if self.wallContact == False:
                self.wallJump = False
                self.WGAngle = None
                self.wallray.setPos(0,1,0)
                    # j = mpoint.getPositionWorldOnA()-self.char.getPos(render)
                    # jx = j.x *10
                    # jy = j.y*10
                    # print(jx, jy)
                    # print(mpoint.getLocalPointB(),mpoint.getPositionWorldOnA(),'charpos:',self.char.getPos(render))
        #spit out a jump dir            
                              
                    
        # print(self.wallContact)
        #             print('walljump')
        # #     print(wallcontact.getNode0())

        # print('walljump?', self.wallContact)
        # sorted_hits = sorted(result.getHits(), key = lambda hit: (pfrom - hit.getHitPos()).length())
        norm = ledgecontact.getHitNormal().z    
        if not ledgecontact.hasHit():
            self.enableVaulting=False
            return
        
        # print('ledgegrab norma;l',norm)
        elif norm == 1:
        
        # else:
            self.enableVaulting=True
            print('vault enabled')
        self.ledgeZ = ledgecontact.getHitPos().z
        # w= self.ledgeZ-self.char.getZ(render)
        # print(self.ledgeZ)

    # def doVault(self):
    #     # self.isVaulting =True
    #     if self.enableVaulting == True:
    #         # self.ledgegrab = self.ledgeZ-self.char.getZ(render)#this is where ur guys hands should go
    #         # to be like fortnite: multiply vec by char direction, no need to hold a button
    #         # if self.vaultvec == None:
    #         vaultvec = Vec3(0,0,7) #+ self.char.getQuat().getForward() *30
    #         self.setLinearMovement(vaultvec)
          
    #     else: 
    #         self.endVault()
    def endVault(self):
        self.vaulting = False
        self.char.setPos(0,0,0)
        self.vaultcheckNode.wrtReparentTo(self.char)
        self.vaultcheckNode2.wrtReparentTo(self.char)
        self.ledgeZ = None
        
        self.ledgegrab = None
        if self.vaultseq!=None:
            self.vaultseq.pause()
            self.vaultseq.finish()
            self.vaultseq =None
        if self.movepoints!=3:
            self.movepoints=3
        self.movementState = "endaction"

        # return task.cont

        # if s
        # self.sphereattached=False
        # self.__world.removeGhost(self.vaultSphere.node())
        # self.movementState="grinding"
        # def endvault():
        #     self.isVaulting =False
        #     self.movementState="ground"   
        # print('vault over ledge')
        # vf = Func(self.isVaulting=False)
        ##3 need to move up Vaulttarget.z, then move to vaultsphere (x/y)
        # self.__world.removeRigidBody(self.__walkCapsuleNP.node())
        
        # # posZ = (self.vaulttarget.z - self.movementParent.getPos().z)
        # vaultup = LerpPosInterval(self.movementParent, 
        # 1,
        # self.vaulttarget )
        # camup = LerpPosInterval(base.camera, 
        # 1,
        # self.vaulttarget )
        # charup = LerpPosInterval(self.char, 
        # 1,
        # self.vaulttarget )
        # seq = Sequence(Parallel(camup,vaultup ),Func(endvault))
        # seq.start()
        # self.__currentPos = self.movementParent.getPos()
        # print(self.result.getContacts())
    def __standUp(self):
        self.__updateHeadContact()
        
        if self.__headContact is not None and self.__currentPos.z + self.__walkLevitation + self.__walkCapsuleH >= self.__headContact[0].z:
            return
        
        self.isCrouching = False
        
        self.capsule = self.__walkCapsule
        self.capsuleNP = self.__walkCapsuleNP
        
        self.__capsuleH, self.__levitation, self.__capsuleR, self.__h = self.__walkCapsuleH, self.__walkLevitation, self.__walkCapsuleR, self.__walkH
        
        self.__world.removeRigidBody(self.__crouchCapsuleNP.node())
        self.__world.attachRigidBody(self.__walkCapsuleNP.node())
        
        self.__capsuleOffset = self.__capsuleH * 0.5 + self.__levitation
        self.__footDistance = self.__capsuleOffset + self.__levitation
        
        if self.__standUpCallback[0] is not None:
            self.__standUpCallback(*self.__standUpCallback[1], **self.__standUpCallback[2])
    
    
    def __processGround(self):
        if not self.isOnGround():
            self.__fall()
        else:
            self.__currentPos.z = self.__footContact[0].z

        # if self.movementParent!=3:
        self.movemepoints =3
        # if self.sphereattached ==True:
        #  self.__world.removeGhost(self.vaultSphere.node())
        self.jumpdir = 0
        #  self.sphereattached = False
    def ground2fall(self, x):
        # return
        # self.jumpdir = self.char.getQuat().getForward() * x
        # self.jumpdir = render.getRelativeVector(self.char,Vec3(0,10,0))
        self.jumpdir=self.movementParent.getRelativeVector(self.char,Vec3(0,10,0))
        # print('ground2fall',self.char.getQuat().getForward()*10,self.movementParent.getRelativeVector(self.char,Vec3(0,10,0)))
    def __processFalling(self):
        
        # self.wallJump = False

        self.__fallTime += self.__timeStep
        self.fallDelta = self.gravity * (self.__fallTime) ** 2
        
        newPos = Vec3(self.__currentPos)
        newPos.z = self.__fallStartPos + self.fallDelta
        
        self.__currentPos = newPos
        
        #ignore this after air dodge
        self.setLinearMovement(self.__linearVelocity + self.jumpdir)
        # print ('jumpdir',self.jumpdir)
        # ###anim


        if self.isOnGround():
            self.__land()
            # taskMgr.add(self.__land)
            # self.__world.attachRigidBody(self.__walkCapsuleNP.node())   

            if self.__fallCallback[0] is not None:
                self.__fallCallback(self.__fallStartPos, *self.__fallCallback[1], **self.__fallCallback[2])
    
    def __processJumping(self):
        if self.movementState == "vaulting":
            # print(self.char.getCurrentFrame())
            if self.char.getCurrentFrame!=None:
                if self.char.getCurrentFrame()!= None and self.char.getCurrentFrame()<10:
                    return

        if self.__headContact is not None and self.__capsuleTop >= self.__headContact[0].z:
            # This shouldn't happen, but just in case, if we hit the ceiling, we start to fall
            print ("Head bang")
            self.__fall()
            return
        
        oldPos = float(self.__currentPos.z)
        
        self.jumpTime += self.__timeStep
        
        self.__currentPos.z = (self.gravity * self.jumpTime**2) + (self.jumpSpeed * self.jumpTime) + self.jumpStartPos
        
        if round(self.__currentPos.z, 2) >= self.jumpMaxHeight:
            self.__fall()

            # print(self.jumpdir.x) 
            self.jumpdir.x /= 2
            self.jumpdir.y /= 2
        # print('sashjifkhsdafiohfwsda')

        self.setLinearMovement(self.__linearVelocity + self.jumpdir)

        # if self.sphereattached ==False:
        #     self.vaultSphere.reparentTo(self.char)
        #     self.__world.attachGhost(self.vaultSphere.node())
        #     self.sphereattached = True
        # self.setLinearMovement(self.grindvec, )
        # print('true jumpdir', self.gr)

    def __processFlying(self):
        if self.__footContact and self.__currentPos.z - 0.1 < self.__footContact[0].z and self.__linearVelocity.z < 0.0:
            self.__currentPos.z = self.__footContact[0].z
            self.__linearVelocity.z = 0.0
        
        if self.__headContact and self.__capsuleTop >= self.__headContact[0].z and self.__linearVelocity.z > 0.0:
            self.__linearVelocity.z = 0.0
        # print('flying. footcontact:', self.__footContact)
        if self.isOnGround and self.__footContact!=None:
            if self.ascending == False:
             self.__currentPos.z = self.__footContact[0].z
       
             self.mechVec*=2
        # if self.ascending == False and self.__footContact!=None:#not self.isOnGround:
        #     self.__fall()
            # self.stopFly()
            # print('state flying, falliung')
    
    def __checkFutureSpace(self, globalVel):
        globalVel = globalVel * self.futureSpacePredictionDistance
        
        pFrom = Point3(self.capsuleNP.getPos(render) + globalVel)
        pUp = Point3(pFrom + Point3(0, 0, self.__capsuleH * 2.0))
        pDown = Point3(pFrom - Point3(0, 0, self.__capsuleH * 2.0 + self.__levitation))
        
        upTest = self.__world.rayTestClosest(pFrom, pUp)
        downTest = self.__world.rayTestClosest(pFrom, pDown)
        
        if not (upTest.hasHit() and downTest.hasHit):
            return True
        
        upNode = upTest.getNode()
        # if upNode.getMass():
        #     return True
        
        space = abs(upTest.getHitPos().z - downTest.getHitPos().z)
        
        if space < self.__levitation + self.__capsuleH + self.capsule.getRadius():
            return False
        
        return True
    
    
    def __updateFootContact(self):
        # print('footdistance', self.__footDistance)
        pFrom = Point3(self.capsuleNP.getPos(render))
        pTo = Point3(pFrom - Point3(0, 0, self.__footDistance))
        result = self.__world.rayTestAll(pFrom, pTo)
        
        if not result.hasHits():
            self.__footContact = None
            return
        
        sorted_hits = sorted(result.getHits(), key = lambda hit: (pFrom - hit.getHitPos()).length())
        
        for hit in sorted_hits:
            if type(hit.getNode()) is BulletGhostNode:
                continue
                # return
            self.__footContact = [hit.getHitPos(), hit.getNode(), hit.getHitNormal()]
            break
    
    def __updateHeadContact(self):
        pFrom = Point3(self.capsuleNP.getPos(render))
        pTo = Point3(pFrom + Point3(0, 0, self.__capsuleH * 20.0))
        result = self.__world.rayTestAll(pFrom, pTo)
        
        if not result.hasHits():
            self.__headContact = None
            return
        
        sorted_hits = sorted(result.getHits(), key = lambda hit: (pFrom - hit.getHitPos()).length())
        
        for hit in sorted_hits:
            if type(hit.getNode()) is BulletGhostNode:
                continue
            
            self.__headContact = [hit.getHitPos(), hit.getNode()]
            break
    
    def __updateCapsule(self):
        self.movementParent.setPos(self.__currentPos)
        self.capsuleNP.setPos(0, 0, self.__capsuleOffset)
        
        self.__capsuleTop = self.__currentPos.z + self.__levitation + self.__capsuleH * 2.0
    
    def __applyLinearVelocity(self):
        globalVel = self.movementParent.getQuat(render).xform(self.__linearVelocity) * self.__timeStep
       #usew this for grindrail
        # if self.movementState == 'finisher':
        # # if self.relative:
        #     globalVel = render.getQuat().xform(self.__linearVelocity) * self.__timeStep
        # print(self.__linearVelocity)
        if self.predictFutureSpace and not self.__checkFutureSpace(globalVel):
            return
        
        if self.__footContact is not None and self.minSlopeDot and self.movementState != "flying":
            normalVel = Vec3(globalVel)
            normalVel.normalize()
            
            floorNormal = self.__footContact[2]
            absSlopeDot = round(floorNormal.dot(Vec3.up()), 2)
            
            def applyGravity():
                self.__currentPos -= Vec3(floorNormal.x, floorNormal.y, 0.0) * self.gravity * self.__timeStep * 0.1
            
            if absSlopeDot <= self.minSlopeDot:
                applyGravity()
                
                if globalVel != Vec3():
                    globalVelDir = Vec3(globalVel)
                    globalVelDir.normalize()
                    
                    fn = Vec3(floorNormal.x, floorNormal.y, 0.0)
                    fn.normalize()
                    
                    velDot = 1.0 - globalVelDir.angleDeg(fn) / 180.0
                    if velDot < 0.5:
                        self.__currentPos -= Vec3(fn.x * globalVel.x, fn.y * globalVel.y, 0.0) * velDot
                    
                    globalVel *= velDot
            
            elif self.__slopeAffectsSpeed and globalVel != Vec3():
                applyGravity()
        
        self.__currentPos += globalVel
        # print(globalVel)
    def __preventPenetration(self):
        collisions = Vec3()
        
        ##########################################################
        # This is a hacky version for when contactTest didn't work
        for mf in self.__world.getManifolds():
            if not (mf.getNumManifoldPoints() and self.capsuleNP.node() in [mf.getNode0(), mf.getNode1()]):
                continue
             
            sign = 1 if mf.getNode0() == self.capsuleNP.node() else -1
             
            for mpoint in mf.getManifoldPoints():
                direction = mpoint.getPositionWorldOnB() - mpoint.getPositionWorldOnA()
                normal = Vec3(direction)
                normal.normalize()
                 
                if mpoint.getDistance() < 0:
                    collisions -= direction * mpoint.getDistance() * 2.0 * sign
        #################################################################
        self.result = self.__world.contactTest(self.capsuleNP.node())
        # print(self.result.getContacts())
        
        for i, contact in enumerate(self.result.getContacts()):
            if type(contact.getNode1()) is BulletGhostNode:
                continue
            
            mpoint = contact.getManifoldPoint()
            normal = mpoint.getPositionWorldOnB() - mpoint.getPositionWorldOnA()
            
            if mpoint.getDistance() < 0:
                collisions -= normal * mpoint.getDistance()
        
        collisions.z = 0.0
        self.__currentPos += collisions
    


    def __mapMethods(self):
        self.getHpr = self.movementParent.getHpr
        self.getH = self.movementParent.getH
        self.getP = self.movementParent.getP
        self.getR = self.movementParent.getR
        
        self.getPos = self.movementParent.getPos
        self.getX = self.movementParent.getX
        self.getY = self.movementParent.getY
        self.getZ = self.movementParent.getZ
        
        self.getQuat = self.movementParent.getQuat
        
        self.setHpr = self.movementParent.setHpr
        self.setH = self.movementParent.setH
        self.setP = self.movementParent.setP
        self.setR = self.movementParent.setR
        
        self.setQuat = self.movementParent.setQuat
    
    def setPos(self, *args):
        self.movementParent.setPos(*args)
        self.__currentPos = self.movementParent.getPos(render)
    
    def setX(self, *args):
        self.movementParent.setX(*args)
        self.__currentX = self.movementParent.getX(render)
    
    def setY(self, *args):
        self.movementParent.setY(*args)
        self.__currentY = self.movementParent.getY(render)
    
    def setZ(self, *args):
        self.movementParent.setZ(*args)
        self.__currentZ = self.movementParent.getZ(render)
    
    def __setup(self, walkH, crouchH, stepH, R):
        def setData(fullH, stepH, R):
            if fullH - stepH <= R * 2.0:
                length = 0.1
                R = (fullH * 0.5) - (stepH * 0.5)
                lev = stepH + R
            else:
                length = fullH - stepH - R * 2.0
                lev = fullH - R - length / 2.0
            
            return length, lev, R
        
        self.__walkH = walkH
        self.__crouchH = crouchH
        
        self.__walkCapsuleH, self.__walkLevitation, self.__walkCapsuleR = setData(walkH, stepH, R)
        self.__crouchCapsuleH, self.__crouchLevitation, self.__crouchCapsuleR = setData(8, stepH, 3)
        
        self.__capsuleH, self.__levitation, self.__capsuleR, self.__h = self.__walkCapsuleH, self.__walkLevitation, self.__walkCapsuleR, self.__walkH
        
        self.__capsuleOffset = self.__capsuleH * 0.5 + self.__levitation
        self.__footDistance = self.__capsuleOffset + self.__levitation
        
        self.__addElements()
    
    def __addElements(self):
        # Walk Capsule


        self.__walkCapsule = BulletCapsuleShape(self.__walkCapsuleR, self.__walkCapsuleH)
        
        self.__walkCapsuleNP = self.movementParent.attachNewNode(BulletRigidBodyNode('Character'))
        self.__walkCapsuleNP.node().addShape(self.__walkCapsule)
        self.__walkCapsuleNP.node().setKinematic(True)
        # self.__walkCapsuleNP.setCollideMask(BitMask32.allOn())
        self.__walkCapsuleNP.setCollideMask(BitMask32.bit(0))
        
        self.__world.attachRigidBody(self.__walkCapsuleNP.node())
        
        # Crouch Capsule
        self.__crouchCapsule = BulletCapsuleShape(self.__crouchCapsuleR, self.__crouchCapsuleH)
        
        self.__crouchCapsuleNP = self.movementParent.attachNewNode(BulletRigidBodyNode('crouchCapsule'))
        self.__crouchCapsuleNP.node().addShape(self.__crouchCapsule)
        self.__crouchCapsuleNP.node().setKinematic(True)
        self.__crouchCapsuleNP.setCollideMask(BitMask32.allOn())

        #Sphere for vaulting over -- using ray instead

        # sphere = BulletSphereShape(.5)
        # self.vaultSphere = self.movementParent.attachNewNode(BulletGhostNode('vault sphere'))
        # self.vaultSphere.node().addShape(sphere)
        # self.vaultSphere.setPos(0,3,4)

        # self.__world.attachGhost(self.vaultSphere.node())
        # self.sphereattached = True
        
        # Set default
        self.capsule = self.__walkCapsule
        self.capsuleNP = self.__walkCapsuleNP
        # self.capsuleNP.setZ(10)

        # Init
        self.__updateCapsule()
