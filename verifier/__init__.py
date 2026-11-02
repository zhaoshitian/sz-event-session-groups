from contract import Task, Tool

from . import operation


def verify_input(tool, value):
    Tool(tool)
    return operation.verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    Tool(tool)
    return operation.verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    Task(task)
    return operation.verify_task(arguments, output, reference, workspace)
