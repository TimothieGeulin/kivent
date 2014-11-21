import os
os.environ['KIVY_AUDIO'] = 'pygame'

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from random import randint, choice
from math import radians, pi, sin, cos, sqrt
import kivent_core
import kivent_cymunk
import cymunk as cy

from kivent_core.renderers import texture_manager, VertMesh
texture_manager.load_image('assets/png/lingrad.png')
texture_manager.load_image('assets/png/lingrad_alt.png')
texture_manager.load_image('assets/png/puck.png')
texture_manager.load_image('assets/png/paddle.png')
texture_manager.load_image('assets/png/airhole.png')
from kivent_cymunk.physics import CymunkPhysics
from functools import partial

import sounds
import menus


class TestGame(Widget):
    def __init__(self, **kwargs):
        super(TestGame, self).__init__(**kwargs)
        self.current_menu_ref = None
        self.bottom_action_name = "speedup"
        self.top_action_name = "speedup"
        Clock.schedule_once(self.init_game)

    def ensure_startup(self):
        systems_to_check = ['map', 'physics', 'renderer', 
            'rotate', 'position', 'gameview', 'lerp_system']
        systems = self.gameworld.systems
        for each in systems_to_check:
            if each not in systems:
                return False
        return True

    def init_game(self, dt):
        if self.ensure_startup():
            self.game_ui_menu = menus.GameUIMenu(self)
            self.setMenu(self.game_ui_menu)
            self.create_scoreboard()
            self.setup_map()
            self.setup_states()
            self.set_state()
            self.draw_some_stuff()
            self.setup_collision_callbacks()
            Clock.schedule_interval(self.update, 0)
        else:
            Clock.schedule_once(self.init_game)
    def getWorldPosFromTuple(self, tup):

        viewport = self.gameworld.systems['gameview']
        return tup[0]*viewport.camera_scale - viewport.camera_pos[0], tup[1]*viewport.camera_scale - viewport.camera_pos[1]
    def getShapeAt(self, xy):
        position = cy.Vec2d(xy[0],xy[1])
        space = self.gameworld.systems['physics'].space
        return space.point_query_first(position)
    def getShapesAt(self, xy):
        return self.getShapesAtVec(cy.Vec2d(xy[0],xy[1]))
    def getShapesAtVec(self, position):
        space = self.gameworld.systems['physics'].space
        b = cy.Body()
        b.position = position
        shapeos = cy.Circle(b, 1)
        return space.shape_query(shapeos)


    def on_touch_down(self, touch):
        if self.current_menu_ref:
            clicked_on_menu = self.current_menu_ref.on_touch_down(touch)
            if clicked_on_menu:return
        wp = self.getWorldPosFromTuple(touch.pos)
        xspos = touch.spos[0]
        yspos = touch.spos[1]
        if xspos<0.08 or xspos>0.92:#far left or right
            if 0.35<yspos<0.65:#on a goal
                paddleid = self.create_paddle(wp, color=(1.-xspos,0.,xspos,1.), player=int(xspos+0.5))
                super(TestGame, self).on_touch_down(touch)
            #else:
            #    self.playermenu.on_touch_down(touch)
        #elif 0.45<yspos<0.55 and 0.47<xspos<0.53:#clicked in middle
        #    self.setMenu(menus.PauseMenu(self))
        elif xspos<0.4 or xspos>0.6:#general player area
            super(TestGame, self).on_touch_down(touch)
        else:#middle area,for observers
            if yspos<0.5:
                do_super = self.bottom_action_name in ['wall', 'vortex']
                self.bottom_action(wp,yspos)
            else:
                do_super = self.top_action_name in ['wall', 'vortex']
                self.top_action(wp,yspos)
            if do_super:super(TestGame, self).on_touch_down(touch)
            #self.observermenu.on_touch_down(touch)

    def bottom_action(self,wp=None,yspos=None):
        print "no action bottom"
    def top_action(self,wp=None,yspos=None):
        print "no action top"
    def action_speedup(self,wp=None,yspos=None):
        touched_shapes = self.getShapesAt(wp)
        for touched_shape in touched_shapes:
            tbody = touched_shape.body
            if tbody.data in self.puckIDs:
                sounds.play_pitchraise(.5)
                tbodyvel = tbody.velocity
                tbodyspeed = sqrt(tbodyvel.x**2.+tbodyvel.y**2.)
                multi=2.
                if tbodyspeed<50.:
                    multi=5.
                elif tbodyspeed<200.:
                    multi=3.
                #print "multi=", multi, " tshape=",touched_shape
                tbody.velocity=(tbodyvel.x*multi,tbodyvel.y*multi)
                if yspos<0.5:
                    self.bottom_points+=tbodyspeed
                else:
                    self.top_points+=tbodyspeed
                self.observermenu.update_scores()
    def action_vortex(self,wp=None,yspos=None):
        vortex_id = self.create_floater(wp,mass=1000,collision_type=7,radius=100,color=(0.1,.1,0.1,0.75))#radius=points
        pfunc = partial( self.remove_entity, vortex_id,0.)
        Clock.schedule_once(pfunc,5)
        self.pfuncs[vortex_id]=pfunc
        if yspos<0.5:
            self.bottom_points-=1000
            self.set_observer_action(1)
        else:
            self.top_points-=1000
            self.set_observer_action(0)
        self.observermenu.update_scores()
    def action_wall(self,wp=None,yspos=None):
        #self.create_floater(wp)
        wallid = self.draw_wall(20,200,wp,(0,1,0,0.5),250,collision_type=6, texture='lingrad_alt')
        self.miscIDs.add(wallid)
        if yspos<0.5:
            self.bottom_points-=5000
            self.set_observer_action(1)
        else:
            self.top_points-=5000
            self.set_observer_action(0)
        self.observermenu.update_scores()
    def action_puck_storm(self,wp=None,yspos=None):
        for i in range(7):
            self.create_puck((wp[0], wp[1]))
        if yspos<0.5:
            self.bottom_points-=10000
            self.set_observer_action(1)
        else:
            self.top_points-=10000
            self.set_observer_action(0)
        self.observermenu.update_scores()
    def on_touch_up(self, touch):
        super(TestGame, self).on_touch_up(touch)
        if 'touched_ent_id' in touch.ud:
            touched_id = touch.ud['touched_ent_id']
            if touched_id in self.paddleIDs:
                if 0.3<touch.spos[1]<0.7 and touch.spos[0]<0.08 or touch.spos[0]>0.92:
                        self.remove_entity(touched_id)
                else:
                    tbody = self.gameworld.entities[touched_id].physics.body
                    tbodyvel = tbody.velocity
                    tbody.velocity=(tbodyvel.x*1.4,tbodyvel.y*1.4)
    def set_observer_action(self, isbottom, action="speedup"):
        #if action=="speedup":
        #actionref=self.action_speedup
        self.observermenu.set_selector_pos(isbottom,action)
        actionref=getattr(self,"action_"+action)
        if isbottom:
            self.bottom_action = actionref
            self.bottom_action_name = action
        else:
            self.top_action = actionref
            self.top_action_name = action


    def create_scoreboard(self):
        mainscreen = self.ids['gamescreenmanager'].ids['main_screen']#.mainlayout

        self.scoreboard = scoreboard = menus.ScoreBoard(self)
        mainscreen.add_widget(scoreboard)
        self.observermenu = self.game_ui_menu.observer_menu #observermenu = menus.ObserverMenu(self)
        #mainscreen.add_widget(observermenu)
        self.playermenu = self.game_ui_menu.player_menu# playermenu = menus.PlayerMenu(self)
        #mainscreen.add_widget(playermenu)
    def setMenu(self, newMenu):
        mainscreen = self.ids['gamescreenmanager'].ids['main_screen']#.mainlayout

        if self.current_menu_ref:
            print 'removing menu', self.current_menu_ref.sname,  str(self.current_menu_ref)
            self.current_menu_ref.on_deactivate()
            mainscreen.remove_widget(self.current_menu_ref)
        mainscreen.add_widget(newMenu)
        self.current_menu_ref = newMenu
        print 'setting menu', self.current_menu_ref.sname,  str(self.current_menu_ref)
        self.current_menu_ref.on_activate()
    def setup_collision_callbacks(self):
        systems = self.gameworld.systems
        physics_system = systems['physics']
        def rfalse(na,nb):
             return False
        #1 - puck
        #2 - wall
        #3 - airhole
        #4 - goal
        #5 - real goal
        #6 - paddle
        #7 - vortex
        physics_system.add_collision_handler(
            1, 3, 
            begin_func=self.begin_collide_with_airhole,
            separate_func=self.begin_seperate_with_airhole)
        physics_system.add_collision_handler(
            1, 2,
            post_solve_func=self.postsolve_collide_sound)
        physics_system.add_collision_handler(
            1, 4, 
            begin_func=self.begin_collide_with_goal)
        physics_system.add_collision_handler(
            1, 7,
            pre_solve_func=self.presolve_collide_with_vortex)
        physics_system.add_collision_handler(
            6, 7,
            pre_solve_func=self.presolve_collide_with_vortex)
        physics_system.add_collision_handler(
            7, 3,
            begin_func=self.begin_collide_with_airhole,
            separate_func=self.begin_seperate_with_airhole)
        physics_system.add_collision_handler(
            1, 5, 
            begin_func=self.begin_collide_with_real_goal)
        physics_system.add_collision_handler(
            1, 6,
            post_solve_func=self.postsolve_collide_sound)
        physics_system.add_collision_handler(
            6, 6,
            post_solve_func=self.postsolve_collide_sound)
        physics_system.add_collision_handler(
            1, 1,
            post_solve_func=self.postsolve_collide_sound)
        physics_system.add_collision_handler(
            6, 2,
            post_solve_func=self.postsolve_collide_sound)
        physics_system.add_collision_handler(
            6, 3,
            begin_func=self.begin_collide_with_airhole,
            separate_func=self.begin_seperate_with_airhole)
        physics_system.add_collision_handler(
            6, 4,
            begin_func=rfalse)
        physics_system.add_collision_handler(
            6, 5,
            begin_func=rfalse)

    def presolve_collide_with_vortex(self, space, arbiter):
        #systems = self.gameworld.systems
        body1 = arbiter.shapes[0].body
        body2 = arbiter.shapes[1].body#vortex
        p1=body1.position
        p2=body2.position
        #ent1_id = body1.data #puck
        #ent2_id = body2.data #goal
        #ents= = self.gameworld.entities
        # apos = entity.position
        dvecx = (p2.x - p1.x) * body1.mass * 0.2
        dvecy = (p2.y - p1.y) * body1.mass * 0.2
        body1.apply_impulse((dvecx, dvecy))

        return False
    def begin_collide_with_goal(self, space, arbiter):
        systems = self.gameworld.systems
        ent1_id = arbiter.shapes[0].body.data #puck
        ent2_id = arbiter.shapes[1].body.data #goal
        lerp_system = systems['lerp_system']
        lerp_system.add_lerp_to_entity(ent2_id, 'color', 'r', 1., .3,
            'float', callback=self.lerp_callback_goal_score)

        return False

    def begin_collide_with_real_goal(self, space, arbiter):
        ent1_id = arbiter.shapes[0].body.data #puck
        ent2_id = arbiter.shapes[1].body.data #goal
        puck = self.gameworld.entities[ent1_id]
        puckposition = puck.physics.body.position
        ppx =  puckposition.x/1920.
        #self.create_puck_fader((puckposition.x,puckposition.y))
        self.remove_entity(ent1_id)
        Clock.schedule_once(self.spawn_new_puck, 2.5)
        sounds.play_jingle()
        if ppx<0.5:
            self.blue_score+=1
            if self.blue_score>9 and self.current_menu_ref.sname=='ingame':
                self.setMenu(menus.VictoryMenu(self,winner="Blue"))
        else:
            self.red_score+=1
            if self.red_score>9 and self.current_menu_ref.sname=='ingame':
                self.setMenu(menus.VictoryMenu(self,winner="Red"))
        self.scoreboard.update_scores()
        return False

    def spawn_new_puck(self, dt):
        puck_id = self.create_puck((1920.*.5, 1080.*.5))
        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']
        lerp_system.add_lerp_to_entity(puck_id, 'color', 'g', .4, 5.,
            'float', callback=self.lerp_callback)

    def begin_collide_with_airhole(self, space, arbiter):
        ent1_id = arbiter.shapes[0].body.data #puck
        ent2_id = arbiter.shapes[1].body.data #airhole
        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']
        lerp_system.clear_lerps_from_entity(ent2_id)
        lerp_system.add_lerp_to_entity(ent2_id, 'color', 'a', .85, .2,
            'float', callback=self.lerp_callback_airhole)
        lerp_system.add_lerp_to_entity(ent2_id, 'scale', 's', 1.2, .3,
            'float')#, callback=self.lerp_callback_airhole_scale)#
        #if ent1_id not in self.paddleIDs: sounds.play_click(.2)
        #else:
        ent = self.gameworld.entities[ent1_id]
        lerp_system.add_lerp_to_entity(ent2_id, 'color', 'b', ent.color.b, .2,
            'float', callback=self.lerp_callback_airhole)
        lerp_system.add_lerp_to_entity(ent2_id, 'color', 'r', ent.color.r, .2,
            'float', callback=self.lerp_callback_airhole)

        return False
    def postsolve_collide_sound(self, space, arbiter):
        #ent1_id = arbiter.shapes[0].body.data #puck
        #ent2_id = arbiter.shapes[1].body.data #paddle
        crashforce =  arbiter.total_ke
        vol = min(1,crashforce/50000000)
        if vol<0.1:return
        if arbiter.is_first_contact:
            sounds.play_thack(vol)
        else:
            sounds.vol_thack(vol)
        return True

    def lerp_callback_goal_score(self, entity_id, component_name, property_name,
        final_value):
        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']
        if final_value > .95:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, .50, .25, 'float', 
                callback=self.lerp_callback_goal_score)
        elif final_value > .85:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, .40, .25, 'float', 
                callback=self.lerp_callback_goal_score)
        elif final_value > .75:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, .30, .25, 'float', 
                callback=self.lerp_callback_goal_score)
        elif final_value > .65:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, .20, .25, 'float', 
                callback=self.lerp_callback_goal_score)
        elif final_value < .25:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, 0., 1., 'float', )
        elif final_value < .35:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, .70, .5, 'float', 
                callback=self.lerp_callback_goal_score)
        elif final_value < .45:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, .80, .5, 'float', 
                callback=self.lerp_callback_goal_score)
        elif final_value < .55:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, .90, .5, 'float', 
                callback=self.lerp_callback_goal_score)
        else:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, 0., 1., 'float', )
        

    def lerp_callback_airhole(self, entity_id, component_name, property_name, 
        final_value):
        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']
        lerp_system.add_lerp_to_entity(entity_id, 'color', 'a', .25, 5.5,
            'float')
        lerp_system.add_lerp_to_entity(entity_id, 'scale', 's', .5, 5.5,
            'float')
    '''def lerp_callback_airhole_scale(self, entity_id, component_name, property_name,
        final_value):
        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']'''

    def begin_seperate_with_airhole(self, space, arbiter):
        ent1_id = arbiter.shapes[0].body.data #puck
        ent2_id = arbiter.shapes[1].body.data #airhole
        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']
        lerp_system.clear_lerps_from_entity(ent2_id)
        lerp_system.add_lerp_to_entity(ent2_id, 'color', 'a', .25, 2.5,
            'float')
        lerp_system.add_lerp_to_entity(ent2_id, 'scale', 's', .5, 2.5,
            'float')
        return False
    def clear_game(self):
        Clock.unschedule(self.spawn_new_puck)
        self.blue_score = 0
        self.red_score = 0
        self.bottom_points = 11000
        self.top_points = 4000
        for p in set(self.paddleIDs):
            self.remove_entity(p)
        for p in set(self.puckIDs):
            self.remove_entity(p)
        for p in set(self.miscIDs):
            self.remove_entity(p)
        self.scoreboard.update_scores()
        self.observermenu.update_scores()
        self.set_observer_action(0)
        self.set_observer_action(1)
    def new_game(self, puck_number=1, paddle_multiplier=1):
        self.clear_game()
        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']

        for yposd in range(1,puck_number+1):
            ypos = float(yposd)/float(puck_number+1)
            puck_id = self.create_puck((1920.*.5, 1080.*ypos))
            lerp_system.add_lerp_to_entity(puck_id, 'color', 'g', .4, 5.,
                'float', callback=self.lerp_callback)

        for yposd in range(1,paddle_multiplier+1):
            ypos = float(yposd)/float(paddle_multiplier+1)
            a_paddle_id = self.create_paddle((1920.*.25, 1080.*ypos), color=(1.,0.,0.,1.),player=0)
            a_paddle_id = self.create_paddle((1920.*.75, 1080.*ypos), color=(0.,0.,1.,1.),player=1)

    def draw_some_stuff(self):
        size = Window.size
        self.pfuncs = {}
        self.paddleIDs = set()
        self.puckIDs = set()
        self.miscIDs = set()
        self.created_entities = created_entities = []
        entities = self.gameworld.entities
        self.create_color_circle((1920.*.5, 1080.*.5), color=(0.5,0.5,0.5,0.5))
        goal_height=560
        goal_thickness=150
        real_goal_height=goal_height-90
        real_goal_thickness=goal_thickness-50
        wall_height=(1080/2-goal_height/2.)
        wall_middle=wall_height/2.

        #player limit walls
        self.draw_wall_decoration(20., 1080, (1920*0.4, 1080/2), (1., .5, 0., 0.3))
        self.draw_wall_decoration(20., 1080, (1920*0.6, 1080/2), (0., .5, 1., 0.3))

        #left goal walls
        self.draw_wall(20., wall_height, (goal_thickness, wall_middle), (0., 1., 0., 1.), texture='lingrad_alt')
        self.draw_wall(20., wall_height, (goal_thickness, 1080-wall_middle), (0., 1., 0., 1.), texture='lingrad_alt')
        self.draw_wall(20., goal_height, (20, 1080/2), (0., 1., 0., 1.), texture='lingrad_alt')
        self.draw_wall(goal_thickness, 20., (goal_thickness/2., 1080/2+goal_height/2), (0., 1., 0., 1.), texture='lingrad')
        self.draw_wall(goal_thickness, 20., (goal_thickness/2., 1080/2-goal_height/2), (0., 1., 0., 1.), texture='lingrad')

        #right goal walls
        self.draw_wall(20., wall_height, (1920-goal_thickness, wall_middle), (0., 1., 0., 1.), texture='lingrad_alt')
        self.draw_wall(20., wall_height, (1920-goal_thickness, 1080-wall_middle), (0., 1., 0., 1.), texture='lingrad_alt')
        self.draw_wall(20., goal_height, (1920-20, 1080/2), (0., 1., 0., 1.), texture='lingrad_alt')
        self.draw_wall(goal_thickness, 20., (1920-goal_thickness/2., 1080/2+goal_height/2), (0., 1., 0., 1.), texture='lingrad')
        self.draw_wall(goal_thickness, 20., (1920-goal_thickness/2., 1080/2-goal_height/2), (0., 1., 0., 1.), texture='lingrad')

        self.draw_wall(1920-goal_thickness*2., 20., (1920./2., 10.), (0., 1., 0., 1.), texture='lingrad')
        self.draw_wall(1920-goal_thickness*2., 20., (1920./2., 1080.-10.), (0., 1., 0., 1.), texture='lingrad')
        #self.draw_wall(20., 1080., (10., 1080./2.), (0., 1., 0., 1.))
        #self.draw_wall(20., 1080., (1920.-10., 1080./2.), (0., 1., 0., 1.))
        self.draw_goal((20.+goal_thickness/2., (1080.-goal_height)/2. + goal_height/2.), (goal_thickness, goal_height),
            (0., 1., 0., 1.0))
        self.red_goal_id=self.draw_goal((20.+real_goal_thickness/2., (1080.-real_goal_height)/2. + real_goal_height/2.), (real_goal_thickness, real_goal_height),
            (1., 0., 0., .25), collision_type=5)
        self.draw_goal((1920. - (20.+goal_thickness/2.), (1080.-goal_height)/2. + goal_height/2.), 
            (goal_thickness, goal_height), (0., 1., 0., 1.0))
        self.blue_goal_id = self.draw_goal((1920. - (20.+real_goal_thickness/2.), (1080.-450.)/2. + 450./2.),
            (real_goal_thickness, 450.), (1., 0., 0., .25), collision_type=5)
        x1 = 225
        y1 = 95
        xnum=20#4-100?
        ynum=xnum*1060/1740+1
        xstep = (1920-x1*2)/float(xnum-1)
        ystep = (1080-y1*2)/float(ynum-1)
        for x in range(xnum):
            for y in range(ynum):
                pos = (x1 + xstep *x, y1 + ystep*y)
                self.create_air_hole(pos)
                #self.create_air_triangle(pos)
        self.new_game()

    def draw_goal(self, pos, size, color, collision_type=4):
        x_vel = 0 #randint(-100, 100)
        y_vel = 0 #randint(-100, 100)
        angle = 0 #radians(randint(-360, 360))
        angular_velocity = 0 #radians(randint(-150, -150))
        width, height = size
        shape_dict = {'width': width, 'height': height, 
            'mass': 0, 'offset': (0, 0)}
        col_shape = {'shape_type': 'box', 'elasticity': .5, 
            'collision_type': collision_type, 'shape_info': shape_dict, 
            'friction': 1.0}
        col_shapes = [col_shape]
        physics_component = {'main_shape': 'box', 
            'velocity': (x_vel, y_vel), 
            'position': pos, 'angle': angle, 
            'angular_velocity': angular_velocity, 
            'vel_limit': 0., 
            'ang_vel_limit': radians(0.), 
            'mass': 0, 'col_shapes': col_shapes}
        create_component_dict = {'physics': physics_component, 
            'renderer': {'size': (width, height),'render': True}, 
            'position': pos, 'rotate': 0, 'color': color,
            'lerp_system': {},
            'scale':1}
        component_order = ['position', 'rotate', 'color',
            'physics', 'renderer', 'lerp_system','scale']
        return self.gameworld.init_entity(create_component_dict, 
            component_order)

    def remove_entity(self, entity_id, a=0,b=0):
        systems = self.gameworld.systems
        ents = self.gameworld.entities
        ent = ents[entity_id]
        if entity_id in self.pfuncs:
            Clock.unschedule(self.pfuncs[entity_id])
            del self.pfuncs[entity_id]
        if hasattr(ent, 'lerp_system'):
            lerp_system = systems['lerp_system']
            lerp_system.clear_lerps_from_entity(entity_id)
        else:
            print "WARNING! no lerp_system on ent:", entity_id
        if entity_id in self.paddleIDs:
            self.paddleIDs.remove(entity_id)
        if entity_id in self.puckIDs:
            self.puckIDs.remove(entity_id)
        if entity_id in self.miscIDs:
            self.miscIDs.remove(entity_id)
        #self.gameworld.remove_entity(entity_id)
        Clock.schedule_once(partial(
            self.gameworld.timed_remove_entity, entity_id))
    def lerp_callback_remove_ent(self, entity_id, component_name, property_name,
        final_value):
        self.remove_entity(entity_id)
    def lerp_callback(self, entity_id, component_name, property_name, 
        final_value):
        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']
        if final_value <= .5:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, 1., 5., 'float', callback=self.lerp_callback)
        else:
            lerp_system.add_lerp_to_entity(entity_id, component_name, 
                property_name, .1, 5., 'float', callback=self.lerp_callback)

    def draw_wall(self, width, height, pos, color, mass=0, collision_type=2, texture='lingrad'):
        x_vel = 0 #randint(-100, 100)
        y_vel = 0 #randint(-100, 100)
        angle = 0 #radians(randint(-360, 360))
        angular_velocity = 0 #radians(randint(-150, -150))
        shape_dict = {'width': width, 'height': height, 
            'mass': mass, 'offset': (0, 0)}
        col_shape = {'shape_type': 'box', 'elasticity': .8,
            'collision_type': collision_type, 'shape_info': shape_dict, 'friction': 1.0}
        col_shapes = [col_shape]
        physics_component = {'main_shape': 'box', 
            'velocity': (x_vel, y_vel), 
            'position': pos, 'angle': angle, 
            'angular_velocity': angular_velocity, 
            'vel_limit': 1500.,
            'ang_vel_limit': radians(200.),
            'mass': mass, 'col_shapes': col_shapes}
        create_component_dict = {'physics': physics_component, 
            'renderer': {'size': (width, height),'render': True, 'texture':texture},
            'position': pos, 'rotate': 0, 'color': color,
            'scale':1}
        component_order = ['position', 'rotate', 'color',
            'physics', 'renderer','scale']
        return self.gameworld.init_entity(create_component_dict, 
            component_order)
    def draw_wall_decoration(self, width, height, pos, color):
        create_component_dict = {
            'renderer': {'size': (width, height),'render': True},
            'position': pos, 'rotate': 0, 'color': color,
            'scale':1}
        component_order = ['position', 'rotate', 'color',
            'renderer','scale']
        return self.gameworld.init_entity(create_component_dict,
            component_order)

    def create_air_triangle(self, pos):
        from random import random
        x_vel = 0 #randint(-100, 100)
        y_vel = 0 #randint(-100, 100)
        angle = random()*11./7. #radians(randint(-360, 360))
        angular_velocity = 0 #radians(randint(-150, -150))
        radius=60
        shape_dict = {'inner_radius': 0, 'outer_radius': radius,
            'mass': 0, 'offset': (0, 0)}
        col_shape = {'shape_type': 'circle', 'elasticity': .5,
            'collision_type': 3, 'shape_info': shape_dict, 'friction': 1.0}
        col_shapes = [col_shape]
        color=(.25, .25, .25, .25)
        vert_mesh = self.draw_regular_polygon(3, radius, color)
        physics_component = {'main_shape': 'circle',
            'velocity': (x_vel, y_vel),
            'position': pos, 'angle': angle,
            'angular_velocity': angular_velocity,
            'vel_limit': 0.,
            'ang_vel_limit': radians(0.),
            'mass': 0, 'col_shapes': col_shapes}
        create_component_dict = {'physics': physics_component,
            'renderer': {'render': True,
            'vert_mesh': vert_mesh#,
            #'size': (radius*2, radius*2)
            },
            'position': pos, 'rotate': angle, 'color': color,
            'lerp_system': {},
            'scale':.5}
        component_order = ['position', 'rotate', 'color',
            'physics', 'renderer', 'lerp_system', 'scale']
        return self.gameworld.init_entity(create_component_dict,
            component_order)
    def create_air_hole(self, pos):
        x_vel = 0 #randint(-100, 100)
        y_vel = 0 #randint(-100, 100)
        angle = 0 #radians(randint(-360, 360))
        angular_velocity = 0 #radians(randint(-150, -150))
        radius=60
        shape_dict = {'inner_radius': 0, 'outer_radius': radius,
            'mass': 0, 'offset': (0, 0)}
        col_shape = {'shape_type': 'circle', 'elasticity': .5, 
            'collision_type': 3, 'shape_info': shape_dict, 'friction': 1.0}
        col_shapes = [col_shape]
        color=(.25, .25, .25, .25)
        #vert_mesh = self.draw_regular_polygon(30, 40., color)
        physics_component = {'main_shape': 'circle', 
            'velocity': (x_vel, y_vel), 
            'position': pos, 'angle': angle, 
            'angular_velocity': angular_velocity, 
            'vel_limit': 0., 
            'ang_vel_limit': radians(0.), 
            'mass': 0, 'col_shapes': col_shapes}
        create_component_dict = {'physics': physics_component, 
            'renderer': {#'texture': 'asteroid1', 
            #'vert_mesh': vert_mesh,
            'size': (radius*2, radius*2),
            'texture': 'airhole'},
            'position': pos, 'rotate': 0, 'color': color,
            'lerp_system': {},
            'scale':.5}
        component_order = ['position', 'rotate', 'color',
            'physics', 'renderer', 'lerp_system', 'scale']
        return self.gameworld.init_entity(create_component_dict, 
            component_order)


    def draw_regular_polygon(self, sides, radius, color):
        x, y = 0., 0.
        angle = 2. * pi / sides
        all_verts = []
        all_verts_a = all_verts.append
        l_pos = list((x, y))
        l_pos.extend(color)
        all_verts_a(l_pos)
        triangles = []
        triangles_a = triangles.extend
        r = radius
        for s in range(sides):
            new_pos = x + r * sin(s * angle), y + r * cos(s * angle)
            l_pos = list(new_pos)
            l_pos.extend((0., 0.))
            l_pos.extend(color)
            all_verts_a(l_pos)
            if s == sides-1:
                triangles_a((s+1, 0, 1))
            else:
                triangles_a((s+1, 0, s+2))
        render_system = self.gameworld.systems['renderer']
        vert_count = len(all_verts)
        index_count = len(triangles)
        vert_mesh =  VertMesh(render_system.attribute_count, 
            vert_count, index_count)
        vert_mesh.indices = triangles
        for i in range(vert_count):
            vert_mesh[i] = all_verts[i]
        return vert_mesh


    def create_floater(self, pos, radius=40,color=(0.9,0.9,0.9,0.3),mass=150,collision_type=6):
        angle = 0 #radians(randint(-360, 360))
        angular_velocity = 0 #radians(randint(-150, -150))
        shape_dict = {'inner_radius': 0, 'outer_radius': radius,
            'mass': mass+0.1, 'offset': (0., 0.)}
        col_shape = {'shape_type': 'circle', 'elasticity': .8,
            'collision_type': collision_type, 'shape_info': shape_dict, 'friction': 1.0}
        col_shapes = [col_shape]
        vert_mesh = self.draw_regular_polygon(30, radius, color)
        physics_component = {'main_shape': 'circle',
            'velocity': (0, 0),
            'position': pos, 'angle': angle,
            'angular_velocity': angular_velocity,
            'vel_limit': 1500.,
            'ang_vel_limit': radians(200),
            'mass': mass, 'col_shapes': col_shapes}
        create_component_dict = {'physics': physics_component,
            'puck_renderer': {#'texture': 'asteroid1',
            'vert_mesh': vert_mesh,
            #'size': (64, 64),
            'render': True},
            'position': pos, 'rotate': 0, 'color': color,
            'lerp_system': {},
            'scale':1}
        component_order = ['position', 'rotate', 'color',
            'physics', 'puck_renderer', 'lerp_system','scale']
        _id =  self.gameworld.init_entity(create_component_dict,
            component_order)

        self.miscIDs.add(_id)
        return _id
    def create_puck(self, pos):
        x_vel = randint(-100, 100)
        y_vel = randint(-100, 100)
        angle = 0 #radians(randint(-360, 360))
        angular_velocity = 0 #radians(randint(-150, -150))
        shape_dict = {'inner_radius': 0, 'outer_radius': 75., 
            'mass': 50, 'offset': (0., 0.)}
        col_shape = {'shape_type': 'circle', 'elasticity': .8,
            'collision_type': 1, 'shape_info': shape_dict, 'friction': 1.0}
        col_shapes = [col_shape]
        #vert_mesh = self.draw_regular_polygon(30, 75., (0., 1., 0., 1.))
        physics_component = {'main_shape': 'circle', 
            'velocity': (x_vel, y_vel), 
            'position': pos, 'angle': angle, 
            'angular_velocity': angular_velocity, 
            'vel_limit': 1500., 
            'ang_vel_limit': radians(200), 
            'mass': 50, 'col_shapes': col_shapes}
        create_component_dict = {'physics': physics_component, 
            'puck_renderer': {#'texture': 'asteroid1', 
            #'vert_mesh': vert_mesh,
            'size': (75*2,75*2),
            'texture':'puck'
            #'render': True
            },
            'position': pos, 'rotate': 0, 'color': (0., 1., 0., 1.),
            'lerp_system': {},
            'scale':1}
        component_order = ['position', 'rotate', 'color',
            'physics', 'puck_renderer', 'lerp_system','scale']
        a_puck_id =  self.gameworld.init_entity(create_component_dict,
            component_order)

        self.puckIDs.add(a_puck_id)
        return a_puck_id


    def create_color_circle(self, pos, radius=50,color=(1., 1., 1., 1.)):
        vert_mesh = self.draw_regular_polygon(30, radius, color)
        create_component_dict = {
            'puck_renderer': {#'texture': 'asteroid1',
            'vert_mesh': vert_mesh,
            #'size': (64, 64),
            'render': True},
            'position': pos, 'rotate': 0, 'color': color,
            'lerp_system': {},
            'scale':1}
        component_order = ['position', 'rotate', 'color',
            'puck_renderer', 'lerp_system','scale']
        eid = self.gameworld.init_entity(create_component_dict,
            component_order)
        return eid
    def create_puck_fader(self, pos, start_alpha=.5,end_alpha=0.,start_scale=1.,end_scale=.1):

        vert_mesh = self.draw_regular_polygon(30, 75., (1., 0., 0., 1.))
        create_component_dict = {
            'puck_renderer': {#'texture': 'asteroid1',
            'vert_mesh': vert_mesh,
            #'size': (64, 64),
            'render': True},
            'position': pos, 'rotate': 0, 'color': (1., 0., 0., start_alpha),
            'lerp_system': {},
            'scale':start_scale}
        component_order = ['position', 'rotate', 'color',
            'puck_renderer', 'lerp_system','scale']
        eid = self.gameworld.init_entity(create_component_dict,
            component_order)

        systems = self.gameworld.systems
        lerp_system = systems['lerp_system']
        lerp_system.clear_lerps_from_entity(eid)
        lerp_system.add_lerp_to_entity(eid, 'color', 'a', end_alpha, 2.5,
            'float', callback=self.lerp_callback_remove_ent)
        lerp_system.add_lerp_to_entity(eid, 'scale', 's', end_scale, 2.4,
            'float')
        return eid

    def springjoint(self, aid,bid,posa=(0,0),posb=(0,0), stren=100, dmp=20):
        ents = self.gameworld.entities
        positiona = cy.Vec2d(posa[0], posa[1])
        positionb = cy.Vec2d(posb[0], posb[1])
        b1 = ents[aid].physics.body
        b2 = ents[bid].physics.body
        #localpos = b1.world_to_local(positiona)
        #localpos = (localpos['x'], localpos['y'])
        #localpos2 = b2.world_to_local(positionb)
        #localpos2 = (localpos2['x'], localpos2['y'])

        #xd = posa[0]-posb[0]
        #yd = posa[1]-posb[1]
        #import math
        dist = 410#math.sqrt(xd*xd+yd*yd)*1.1

        aj = cy.DampedSpring(b1, b2, posa, posb, dist,stren,dmp)
        space = self.gameworld.systems['physics'].space
        space.add(aj)
        return aj
    def create_paddle(self, pos, color=(1,1,1,0.65), player=0):
        angle = 0 #radians(randint(-360, 360))
        angular_velocity = 0 #radians(randint(-150, -150))
        radius=55
        shape_dict = {'inner_radius': 0, 'outer_radius': radius,
            'mass': 50, 'offset': (0., 0.)}
        col_shape = {'shape_type': 'circle', 'elasticity': .8,
            'collision_type': 6, 'shape_info': shape_dict, 'friction': 1.0}
        col_shapes = [col_shape]
        #vert_mesh = self.draw_regular_polygon(30, radius, (1., 0., 0., 1.))
        physics_component = {'main_shape': 'circle',
            'velocity': (0,0),
            'position': pos, 'angle': angle,
            'angular_velocity': angular_velocity,
            'vel_limit': 3000.,
            'ang_vel_limit': radians(200),
            'mass': 50, 'col_shapes': col_shapes}
        create_component_dict = {'physics': physics_component,
            'puck_renderer': {#'texture': 'asteroid1',
            #'vert_mesh': vert_mesh,
            'size': (50*2, 50*2),
            'texture': 'paddle'},
            'position': pos, 'rotate': 0, 'color': color,
            'lerp_system': {},
            'scale':1.}
        component_order = ['position', 'rotate', 'color',
            'physics', 'puck_renderer', 'lerp_system','scale']
        a_paddle_id =  self.gameworld.init_entity(create_component_dict,
            component_order)
        if player==0:
            self.springjoint(a_paddle_id,self.red_goal_id)
        else:
            self.springjoint(a_paddle_id,self.blue_goal_id)
        self.paddleIDs.add(a_paddle_id)
        return a_paddle_id

    def setup_map(self):
        gameworld = self.gameworld
        gameworld.currentmap = gameworld.systems['map']

    def update(self, dt):
        self.gameworld.update(dt)

    def setup_states(self):
        self.gameworld.add_state(state_name='main', 
            systems_added=['renderer', 'puck_renderer'],
            systems_removed=[], systems_paused=[],
            systems_unpaused=['renderer', 'puck_renderer'],
            screenmanager_screen='main')

    def set_state(self):
        self.gameworld.state = 'main'


class YourAppNameApp(App):
    def build(self):
        Window.clearcolor = (0, 0, 0, 1.)


if __name__ == '__main__':
    from kivy.utils import platform
    if platform == 'android':pfile='/sdcard/kivocky.prof'
    else:pfile='kivocky.prof'
    import cProfile
    cProfile.run('YourAppNameApp().run()', pfile)
    #YourAppNameApp().run()