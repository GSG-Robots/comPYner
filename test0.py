# LEGO type:standard slot:0 autostart
# OTTOS PROGRAMMIERUNG IN PYTHON
# pylint: disable=too-many-lines
# pylint: disable=trailing-newlines
"""
Current Program, uses PEP8 conform names and has the new MasterControlProgram class
This is work in progress so there is no docstr on new elements.
"""

from master import MasterControlProgram, Run, PrimeHub, hub, StopRun, BatteryLowError, EnterDebugMenu, DEBUG_MODE, Cm, pi, __Timer, wait_for_seconds, FRONT_LEFT, FRONT_RIGHT, BACK_LEFT, BACK_RIGHT

mcp = MasterControlProgram(
    PrimeHub(), debug_mode=DEBUG_MODE, degree_offset=0, global_speed_multiplier=1
)

timer = __Timer()
timer.reset()


#gtc
@mcp.run()
def run_1(run: Run):
    run.gyro_drive(50, 0, ending_condition=Cm(20), p_correction=1.2)
    run.gyro_drive(-50, 0, ending_condition=Cm(20), p_correction=1.2)



# @mcp.run()
# def run_1(run: Run):
#     """Giftschlange Run (Grün)"""
#     timer.reset()
#     run.gyro_drive(80, 0, ending_condition=Cm(39), p_correction=1.2)
#     wait_for_seconds(1)
#     # run.gyro_turn(20, p_correction=1, speed_multiplier=1.2)
#     run.gyro_turn(45, p_correction=1)
#     # Pult gelöst
#     run.gyro_drive(-50, 45, ending_condition=Cm(3.25), p_correction=1.2)
#     run.gyro_turn(135, p_correction=0.7, speed_multiplier=1.7)
#     wait_for_seconds(1)
#     run.gyro_drive(-80, 135, ending_condition=Cm(29.0), p_correction=1.2)
#     run.gyro_turn(90, p_correction=0.9)
#     # gleich heranfahren an Karusell
#     run.gyro_drive(-45, 90, ending_condition=Cm(8))
#     run.drive_attachment(BACK_RIGHT, -75, True, 1)
#     run.drive_attachment(BACK_LEFT, 35, True, 2)
#     run.gyro_drive(45, 90, ending_condition=Cm(7))
#     run.gyro_turn(135, p_correction=1.4)
#     # ab jetz Rückweg
#     run.gyro_drive(80, 135, ending_condition=Cm(28), p_correction=1.2)
#     run.gyro_turn(180, p_correction=1.4)
#     run.gyro_drive(65, 180, ending_condition=Cm(35), p_correction=1.2)
#     # run.drive_attachment(BACK_LEFT, 100, True, 2)


# @mcp.run()
# def run_2(run: Run):
#     """Biene Mayo"""
#     run.gyro_drive(70, 0, Cm(50.5), p_correction=1.2)
#     run.drive_attachment(BACK_RIGHT, -100, duration=3.1, resistance=True)
#     # Einhaken
#     run.select_gear(BACK_LEFT)
#     run.gyro_drive(-50, 0, Cm(7), p_correction=1.2)
#     run.gyro_turn(23, speed_multiplier=2, speed_multiplier_left=0, p_correction=2)
#     run.gyro_drive(-50, 23, Cm(6), p_correction=1)
#     run.gyro_turn(45, speed_multiplier_right=2, p_correction=2)
#     run.drive_attachment(BACK_RIGHT, 100, duration=2.75)
#     run.gyro_turn(0, speed_multiplier_left=0, p_correction=1)
#     # Kamera abgesetz, weiterfahren
#     run.gyro_drive(70, 0, Cm(19), p_correction=1)
#     run.drive_attachment(FRONT_RIGHT, -100, duration=2.5)
#     run.gyro_drive(70, 0, Cm(4), p_correction=1)
#     run.drive_attachment(BACK_LEFT, -100, duration=0.75)
#     run.gyro_drive(100, 0, Cm(12), p_correction=1.2)
#     # Abbiegen zur Achterbahn
#     # run.gyro_turn(35,p_correction=1.2)
#     run.drive_attachment(FRONT_LEFT, 100, duration=1.5)
#     run.gyro_drive(70, 10, Cm(15), p_correction=1.2)
#     # run.gyro_turn(0, p_correction=1.2)
#     run.gyro_drive(100, 10, Cm(65), p_correction=1.5)


# @mcp.run()
# def run_3(run: Run):
#     # """Third Part of Biene Mayo"""
#     # run.gyro_drive(80, 0, ending_condition=Cm(40), p_correction=3)
#     # run.gyro_drive(-100, 0, ending_condition=Cm(30), p_correction=3)
#     while True:
#         try:
#             ...
#         except KeyboardInterrupt:
#             print("Test")


# @mcp.run(turning_degree_tolerance=1)
# def run_4(run: Run):
#     """Tatütata Run (Rot)"""
#     run.gyro_drive(speed=100, degree=0, ending_condition=Cm(18), p_correction=1.2)
#     run.gyro_drive(speed=50, degree=0, ending_condition=Cm(11), p_correction=1.2)
#     run.gyro_drive(speed=-70, degree=0, ending_condition=Cm(15), p_correction=1.2)
#     # Druckerpresse reingeschoben, fahren zu Lichtshow
#     run.gyro_turn(44, p_correction=0.9)
#     run.gyro_drive(speed=90, degree=44, ending_condition=Cm(30), p_correction=1.2)
#     run.gyro_drive(speed=50, degree=44, ending_condition=Cm(8), p_correction=1.2)
#     run.drive_attachment(FRONT_RIGHT, 100, duration=1)
#     run.gyro_drive(speed=-90, degree=44, ending_condition=Cm(10), p_correction=1.2)
#     run.drive_attachment(FRONT_RIGHT, 100, duration=1.5)
#     # Lichtshow aktiviert, fahren zu Turm
#     run.gyro_turn(0, p_correction=0.9)
#     run.gyro_drive(speed=90, degree=0, ending_condition=Cm(20.5), p_correction=1.2)
#     run.gyro_turn(-45, p_correction=0.9)
#     run.gyro_drive(speed=100, degree=-45, ending_condition=Cm(34), p_correction=1.2)
#     run.gyro_drive(speed=70, degree=-45, ending_condition=Cm(10), p_correction=1.2)
#     run.gyro_turn(45, p_correction=0.6, ending_condition=Sec(3))
#     run.gyro_drive(speed=90, degree=45, ending_condition=Cm(20), p_correction=1)
#     wait_for_seconds(1)
#     run.drive_attachment(FRONT_LEFT, 100, duration=2.5)
#     run.drive_attachment(FRONT_LEFT, -100, duration=2.5)
#     run.drive_attachment(FRONT_RIGHT, -100, duration=1)
#     # Roboter ist ausgerichtet
#     if timer.now() < 130:
#         run.gyro_drive(speed=-75, degree=45, ending_condition=Cm(25), p_correction=1.2)
#         run.drive_attachment(BACK_RIGHT, -100, duration=12.5)
#         # Turm hochgefahren
#         run.gyro_drive(speed=90, degree=45, ending_condition=Sec(1.5), p_correction=1.2)
#         # zurück gefahren
#     else:
#         run.gyro_drive(speed=-75, degree=45, ending_condition=Cm(12), p_correction=1.2)
#         # Blume ermordet
#         run.gyro_drive(speed=90, degree=45, ending_condition=Cm(12), p_correction=1.2)
#     run.gyro_drive(speed=50, degree=45, ending_condition=Cm(1.5), p_correction=1.2)


@mcp.run(display_as="R")
def run_cleaning(run: Run):
    """Cleaning Wheels"""

    def run_for(sec, speed):
        run.driving_motors.start_at_power(speed, 0)
        wait_for_seconds(sec)

    # run_for(.1, 10)
    run_for(0.1, 30)
    run_for(0.1, 50)
    run_for(0.1, 60)
    run_for(0.2, 70)
    run_for(0.2, 80)
    run_for(0.3, 90)
    #    run_for(1, 100)
    run_for(3, 100)
    run_for(0.2, 90)
    run_for(0.2, 80)
    run_for(0.2, 70)
    run_for(0.2, 60)
    run_for(0.2, 50)
    run_for(0.2, 40)
    run_for(0.2, 30)
    run_for(0.2, 20)
    run_for(0.2, 10)

    run.driving_motors.stop()


@mcp.run(display_as="T", debug_mode=False)
def run_test(run: Run):
    """Run all attachment motors"""
    run.drive_attachment(1, 100, duration=1)
    run.drive_attachment(2, 100, duration=1)
    run.drive_attachment(3, 100, duration=1)
    run.drive_attachment(4, 100, duration=1)


@mcp.run(display_as="C", debug_mode=False)
def run_motorcontrol(run: Run):
    """Motorcontrol"""
    select = 1
    last_select = -1
    motor = FRONT_RIGHT
    try:
        while True:
            if run.brick.left_button.is_pressed():
                select -= 1
                run.brick.left_button.wait_until_released()
                wait_for_seconds(0.1)
            if run.brick.right_button.is_pressed():
                select += 1
                run.brick.right_button.wait_until_released()
                wait_for_seconds(0.1)
            if select < 1:
                select = 4
            if select > 4:
                select = 1
            if last_select != select:
                last_select = select
                # mcp.light_up_display(run.brick, motor, 4)
                mcp.brick.light_matrix.off()
                if select == 1:
                    mcp.brick.light_matrix.set_pixel(0, 0, 100)
                    motor = FRONT_LEFT
                if select == 2:
                    mcp.brick.light_matrix.set_pixel(4, 0, 100)
                    motor = FRONT_RIGHT
                if select == 3:
                    mcp.brick.light_matrix.set_pixel(0, 4, 100)
                    motor = BACK_LEFT
                if select == 4:
                    mcp.brick.light_matrix.set_pixel(4, 4, 100)
                    motor = BACK_RIGHT
    except KeyboardInterrupt:
        speed = 100
        is_inverted = motor in (BACK_RIGHT, FRONT_RIGHT)
        mcp.brick.light_matrix.off()
        mcp.brick.light_matrix.show_image("GO_RIGHT" if is_inverted else "GO_LEFT")
        try:
            while True:
                if (
                    run.brick.left_button.is_pressed()
                    and run.brick.right_button.is_pressed()
                ):
                    return
                if run.brick.right_button.is_pressed():
                    speed = 100
                    mcp.brick.light_matrix.show_image(
                        "GO_RIGHT" if is_inverted else "GO_LEFT"
                    )
                if run.brick.left_button.is_pressed():
                    speed = -100
                    mcp.brick.light_matrix.show_image(
                        "GO_LEFT" if is_inverted else "GO_RIGHT"
                    )
        except KeyboardInterrupt:
            try:
                run.drive_attachment(motor, speed)
                while True:
                    wait_for_seconds(0.1)
            except KeyboardInterrupt:
                run.drive_shaft.stop()
                wait_for_seconds(1.0)


@mcp.run(display_as="D", debug_mode=False)
def run_drivetocode(run: Run):
    motor_turn = 0
    while True:
        input_dtc = []
        try:
            while True:
                mcp.brick.light_matrix.show_image("ARROW_N", brightness=100)
                input_dtc.append(
                    (
                        abs(run.right_motor.get_degrees_counted()),
                        abs(run.left_motor.get_degrees_counted()),
                        run.brick.motion_sensor.get_yaw_angle(),
                    )
                )
                wait_for_seconds(0.5)
        except KeyboardInterrupt as error:
            mcp.brick.light_matrix.off()
            mcp.brick.light_matrix.show_image("SQUARE", brightness=100)
            try:
                for x in input_dtc:
                    right_turns += x[0]
                    left_turns += x[1]
                    gyro_value += x[2]
                drived_cm = right_turns + left_turns / 2 / 360 * pi * run.tire_radius
                gyro_value_middle = gyro_value / len(input_dtc)
                if drived_cm < 0.25:
                    print(
                        "run.gyro_turn(degree={gyro_value}, p_correction=0.9)".format(
                            gyro_value=gyro_value
                        )
                    )
                elif left_turns > 0.25:
                    speed_multiplier_right_dtc = right_turns / left_turns
                    print(
                        "run.gyro_turn(degree={gyro_value}, p_correction=0.9), speed_multiplier_right = {speed_multiplier_right_dtc})".format(
                            gyro_value=gyro_value,
                            speed_multiplier_right_dtc=speed_multiplier_right_dtc,
                        )
                    )
                elif right_turns > 0.25:
                    speed_multiplier_left_dtc = left_turns / right_turns
                    print(
                        "run.gyro_turn(degree={gyro_value}, p_correction=0.9), speed_multiplier_left = {speed_multiplier_left_dtc})".format(
                            gyro_value=gyro_value,
                            speed_multiplier_left_dtc=speed_multiplier_left_dtc,
                        )
                    )
                else:
                    print(
                        "run.gyro_drive(speed=100, degree={gyro_value_middle}, ending_condition=Cm({drived_cm}), p_correction=1.2)".format(
                            gyro_value_middle=gyro_value_middle, drived_cm=drived_cm
                        )
                    )
                while True:
                    if run.brick.left_button.was_pressed():
                        motor_turn += 1
                        print("Motor Drehung {0}".format(motor_turn))
                    if run.brick.right_button.was_pressed():
                        raise StopRun from error
            except KeyboardInterrupt:
                ...


@mcp.run(display_as="X", debug_mode=False)
def run_drivetocode(run: Run):
    motor_turn = 0
    while True:
        input_dtc, case_list = []
        try:
            while True:
                mcp.brick.light_matrix.show_image("ARROW_N", brightness=100)
                input_dtc.append(
                    (
                        abs(run.right_motor.get_degrees_counted()),
                        abs(run.left_motor.get_degrees_counted()),
                        run.brick.motion_sensor.get_yaw_angle(),
                    )
                )
                if run.brick.left_button.was_pressed():
                    input_dtc.append("Motor_turn")
                wait_for_seconds(0.5)
        except KeyboardInterrupt as error:
            mcp.brick.light_matrix.off()
            mcp.brick.light_matrix.show_image("SQUARE", brightness=100)
            try:
                for x in input_dtc:
                    if x[0] == "Motor_turn":
                        motor_turn += 1
                        print("Motor Drehung {motor_turn}")
                    if isinstance(x[0], float):
                        if right_turns > 0.1 or left_turns > 0.1:
                            right_turns += x[0]
                            ...
                drived_cm = right_turns + left_turns / 2 / 360 * pi * run.tire_radius
                gyro_value_middle = gyro_value / len(input_dtc)
                if drived_cm < 0.25:
                    print("run.gyro_turn(degree= {gyro_value}, p_correction=0.9)")
                elif left_turns > 0.25:
                    speed_multiplier_right_dtc = right_turns / left_turns
                    print(
                        "run.gyro_turn(degree= {gyro_value}, p_correction=0.9), speed_multiplier_right = {speed_multiplier_right_dtc}) "
                    )
                elif right_turns > 0.25:
                    speed_multiplier_left_dtc = left_turns / right_turns
                    print(
                        "run.gyro_turn(degree= {gyro_value}, p_correction=0.9), speed_multiplier_left = {speed_multiplier_left_dtc})"
                    )
                else:
                    print(
                        "run.gyro_drive(speed=100, degree={gyro_value_middle}, ending_condition=Cm({drived_cm}), p_correction=1.2)"
                    )
            except KeyboardInterrupt:
                ...


debug_menu = MasterControlProgram(PrimeHub())


@debug_menu.run(display_as="R")
def restart(run):  # pylint: disable=unused-argument
    """Restart the robot."""
    hub.power_off(True, True)


@debug_menu.run(display_as="D")
def enbug(run):  # pylint: disable=unused-argument
    """Disable debug menu."""
    mcp.defaults["debug_mode"] = False


while True:
    try:
        mcp.start()
    except BatteryLowError as e:
        mcp.brick.light_matrix.write("!")
        mcp.brick.speaker.beep(65, 1)
        raise e
    except EnterDebugMenu as e:
        try:
            debug_menu.start(no_debug_menu=True)
        except SystemExit:
            continue
    except Exception as e:
        mcp.brick.speaker.beep(65, 0.2)
        wait_for_seconds(0.1)
        mcp.brick.speaker.beep(70, 0.2)
        wait_for_seconds(0.1)
        mcp.brick.speaker.beep(75, 0.1)
        wait_for_seconds(0.1)
        mcp.brick.speaker.beep(80, 0.2)
        mcp.brick.light_matrix.write(str(e))
        raise e