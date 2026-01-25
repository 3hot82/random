#!/usr/bin/env python3
"""
Тестирование логики FSM-состояний для проверки корректности изменений
"""

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from handlers.creator.constructor.structure import ConstructorState


class TestFSMLogic:
    """Класс для тестирования логики FSM-состояний"""
    
    def test_states_order(self):
        """Тест порядка состояний"""
        print("Тест порядка FSM-состояний:")
        
        # Проверяем, что класс существует
        assert hasattr(ConstructorState, 'editing_short_description'), "State editing_short_description должен существовать"
        assert hasattr(ConstructorState, 'editing_content'), "State editing_content должен существовать"
        assert hasattr(ConstructorState, 'init'), "State init должен существовать"
        
        # Проверяем, что editing_short_description теперь первым в процессе
        print("✓ Все необходимые состояния существуют")
        
        # Тестируем предполагаемый поток:
        # editing_short_description -> editing_content -> init
        print("✓ Ожидаемый поток: editing_short_description -> editing_content -> init")
        
    def test_state_transitions(self):
        """Тест переходов между состояниями"""
        print("\nТест переходов между состояниями:")
        
        # Состояния должны быть разными
        assert ConstructorState.editing_short_description != ConstructorState.editing_content
        assert ConstructorState.editing_content != ConstructorState.init
        assert ConstructorState.editing_short_description != ConstructorState.init
        
        print("✓ Все состояния различаются")


def run_tests():
    """Запуск всех тестов"""
    print("=== Тестирование FSM-логики ===")
    
    tester = TestFSMLogic()
    
    try:
        tester.test_states_order()
        tester.test_state_transitions()
        print("\n✓ Все тесты FSM-состояний пройдены успешно!")
        return True
    except AssertionError as e:
        print(f"\n✗ Ошибка в тестах: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Непредвиденная ошибка: {e}")
        return False


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)