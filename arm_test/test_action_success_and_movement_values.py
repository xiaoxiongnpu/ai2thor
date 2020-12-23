import datetime
import pdb

import ai2thor.controller
import ai2thor
import random
import copy
import time
from helper_mover import get_reachable_positions, execute_command, ADITIONAL_ARM_ARGS, get_current_full_state, two_dict_equal, get_current_arm_state

MAX_TESTS = 300
MAX_EP_LEN = 1000
# scene_indices = [i + 1 for i in range(30)] #Only kitchens
scene_indices = [i + 1 for i in range(30)] +[i + 1 for i in range(200,230)] +[i + 1 for i in range(300,330)] +[i + 1 for i in range(400,430)]
scene_names = ['FloorPlan{}_physics'.format(i) for i in scene_indices]
set_of_actions = ['mm', 'rr', 'll', 'w', 'z', 'a', 's', 'u', 'j', '3', '4', 'p']

controller = ai2thor.controller.Controller(
    scene=scene_names[0], gridSize=0.25,
    width=900, height=900, agentMode='arm', fieldOfView=100,
    agentControllerType='mid-level',
    server_class=ai2thor.fifo_server.FifoServer,
    useMassThreshold = True, massThreshold = 10, #TODO we need to add this everywhere
)





def reset_the_scene_and_get_reachables(scene_name=None):
    if scene_name is None:
        scene_name = random.choice(scene_names)
    controller.reset(scene_name)
    return get_reachable_positions(controller)

all_timers = []

for i in range(MAX_TESTS):
    reachable_positions = reset_the_scene_and_get_reachables()

    failed_action_pool = []

    all_commands = []
    all_exact_command = []

    initial_location = random.choice(reachable_positions)
    initial_rotation = random.choice([i for i in range(0, 360, 45)])
    event1 = controller.step(action='TeleportFull', x=initial_location['x'], y=initial_location['y'], z=initial_location['z'], rotation=dict(x=0, y=initial_rotation, z=0), horizon=10)
    initial_pose = dict(action='TeleportFull', x=initial_location['x'], y=initial_location['y'], z=initial_location['z'], rotation=dict(x=0, y=initial_rotation, z=0), horizon=10)
    all_exact_command.append(initial_pose)
    controller.step('PausePhysicsAutoSim')

    before = datetime.datetime.now()
    for j in range(MAX_EP_LEN):
        command = random.choice(set_of_actions)
        before_action_arm_value = get_current_arm_state(controller)#.copy() #TODO this is important
        before_full = copy.deepcopy(controller.last_event.metadata['arm'])
        output_of_command = execute_command(controller, command, ADITIONAL_ARM_ARGS)
        all_exact_command.append(output_of_command)
        all_commands.append(command)
        last_event_success = controller.last_event.metadata['lastActionSuccess']
        after_action_arm_value = get_current_arm_state(controller)
        after_full = copy.deepcopy(controller.last_event.metadata['arm'])

        if last_event_success and command in ['w','z', 'a', 's', '3', '4', 'u', 'j']:
            expected_arm_position = before_action_arm_value.copy()
            move_arm_value = ADITIONAL_ARM_ARGS['move_constant']
            if command == 'w':
                expected_arm_position['z'] += move_arm_value
            elif command == 'z':
                expected_arm_position['z'] -= move_arm_value
            elif command == 's':
                expected_arm_position['x'] += move_arm_value
            elif command == 'a':
                expected_arm_position['x'] -= move_arm_value
            elif command == '3':
                expected_arm_position['y'] += move_arm_value
            elif command == '4':
                expected_arm_position['y'] -= move_arm_value
            elif command == 'u':
                expected_arm_position['h'] += move_arm_value
            elif command == 'j':
                expected_arm_position['h'] -= move_arm_value
            # expected_arm_position['h'] = max(min(expected_arm_position['h'], 1), 0) # remove this, we want the action to fail
            # this means the result value is closer to the expected pose with an arm movement margin
            # if not two_dict_equal(expected_arm_position, after_action_arm_value, threshold=ADITIONAL_ARM_ARGS['move_constant']):

                # print('Arm movement error')
                # print('before', before_action_arm_value, '\n after', after_action_arm_value, '\n expected', expected_arm_position, '\n action', command, 'success', last_event_success)
                # pdb.set_trace()

            if command in ['u', 'j'] and not two_dict_equal(expected_arm_position, after_action_arm_value, threshold=0.01):

                print('Arm height movement error')
                print('before', before_action_arm_value, '\n after', after_action_arm_value, '\n expected', expected_arm_position, '\n action', command, 'success', last_event_success)
                pdb.set_trace()
        else:
            expected_arm_position = before_action_arm_value.copy()
            if not two_dict_equal(expected_arm_position, after_action_arm_value, threshold=0.001):#TODO ADITIONAL_ARM_ARGS['move_constant'] / 2):
                print('Failed action or non-arm movement errors')
                print('before', before_action_arm_value, '\n after', after_action_arm_value, '\n expected', expected_arm_position, '\n action', command, 'success', last_event_success)
                pdb.set_trace()


        pickupable = controller.last_event.metadata['arm']['PickupableObjectsInsideHandSphere']
        picked_up_before = controller.last_event.metadata['arm']['HeldObjects']
        if len(pickupable) > 0 and len(picked_up_before) == 0:
            cmd = 'p'
            output_of_command = execute_command(controller, cmd, ADITIONAL_ARM_ARGS)
            all_exact_command.append(output_of_command)
            all_commands.append(cmd)
            if controller.last_event.metadata['lastActionSuccess'] is False:
                print('Failed to pick up ')
                print('scene name', controller.last_event.metadata['sceneName'])
                print('initial pose', initial_pose)
                print('list of actions', all_commands)
                break





    after = datetime.datetime.now()
    time_diff = after - before
    seconds = time_diff.total_seconds()
    all_timers.append(len(all_commands) / seconds)
    print('FPS', sum(all_timers) / len(all_timers))


