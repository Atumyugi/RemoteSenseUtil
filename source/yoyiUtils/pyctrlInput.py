import pynput
from pynput.keyboard import Controller, Key, Listener
from pynput.mouse import Button

def on_click(x, y, button, pressed):
    if button == Button.left:
        kb = Controller()
        # 使用键盘输入一个字母
        kb.press(Key.ctrl)
        kb.press(Key.alt)
        kb.press('.')
        kb.release(Key.ctrl)
        kb.release(Key.alt)
        kb.release('.')
        kb.pressed(Key.ctrl,Key.alt,'.')
    if button == Button.right:
        kb = Controller()
        # 使用键盘输入一个字母
        kb.press(Key.ctrl)
        kb.press('m')
        kb.release(Key.ctrl)
        kb.release('m')
        kb.pressed(Key.ctrl,'m')
        return False

# with pynput.keyboard.Listener(on_click=on_click,) as keyListener
#     keyListener.join()

# with pynput.keyboard.Listener(on_click=on_click,) as keyListener
#     keyListener.join()
# 监听鼠标事件
with pynput.mouse.Listener(on_click=on_click,) as listener:
    listener.join()

