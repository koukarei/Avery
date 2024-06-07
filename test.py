# import gradio as gr

# with gr.Blocks() as demo:
    
#     tasks = gr.State([])
#     new_task = gr.Textbox(label="Task Name", autofocus=True)

#     def add_task(tasks, new_task_name):
#         return tasks + [{"name": new_task_name, "complete": False}], ""

#     new_task.submit(add_task, [tasks, new_task], [tasks, new_task])

#     @gr.render(inputs=tasks)
#     def render_todos(task_list):
#         complete = [task for task in task_list if task["complete"]]
#         incomplete = [task for task in task_list if not task["complete"]]
#         gr.Markdown(f"### Incomplete Tasks ({len(incomplete)})")
#         for task in incomplete:
#             with gr.Row():
#                 gr.Textbox(task['name'], show_label=False, container=False)
#                 done_btn = gr.Button("Done", scale=0)
#                 def mark_done(task=task):
#                     task["complete"] = True
#                     return task_list
#                 done_btn.click(mark_done, None, [tasks])

#                 delete_btn = gr.Button("Delete", scale=0, variant="stop")
#                 def delete(task=task):
#                     task_list.remove(task)
#                     return task_list
#                 delete_btn.click(delete, None, [tasks])

#         gr.Markdown(f"### Complete Tasks ({len(complete)})")
#         for task in complete:
#             gr.Textbox(task['name'], show_label=False, container=False)




# demo.launch()

# # with gr.Blocks() as demo:
# #     with gr.Tab("Lion"):
# #         gr.Image("lion.jpg")
# #         gr.Button("New Lion")
# #     with gr.Tab("Tiger"):
# #         gr.Image("tiger.jpg")
# #         gr.Button("New Tiger")

# # demo.launch()

# import gradio as gr

# with gr.Blocks() as demo:
#     input_text = gr.Textbox()

#     @gr.render(inputs=input_text)
#     def show_split(text):
#         if len(text) == 0:
#             gr.Markdown("## No Input Provided")
#         else:
#             for letter in text:
#                 with gr.Row():
#                     text = gr.Textbox(letter)
#                     btn = gr.Button("Clear")
#                     btn.click(lambda: gr.Textbox(value=""), None, text)

# demo.launch()

# import gradio as gr

# def tax_calculator(income, marital_status, assets):
#     tax_brackets = [(10, 0), (25, 8), (60, 12), (120, 20), (250, 30)]
#     total_deductible = sum(assets["Cost"])
#     taxable_income = income - total_deductible

#     total_tax = 0
#     for bracket, rate in tax_brackets:
#         if taxable_income > bracket:
#             total_tax += (taxable_income - bracket) * rate / 100

#     if marital_status == "Married":
#         total_tax *= 0.75
#     elif marital_status == "Divorced":
#         total_tax *= 0.8

#     return round(total_tax)

# demo = gr.Interface(
#     tax_calculator,
#     [
#         "number",
#         gr.Radio(["Single", "Married", "Divorced"]),
#         gr.Dataframe(
#             headers=["Item", "Cost"],
#             datatype=["str", "number"],
#             label="Assets Purchased this Year",
#         ),
#     ],
#     "number",
#     examples=[
#         [10000, "Married", [["Suit", 5000], ["Laptop", 800], ["Car", 1800]]],
#         [80000, "Single", [["Suit", 800], ["Watch", 1800], ["Car", 800]]],
#     ],
# )

# demo.launch()

import gradio as gr

# Code for Task 1
def task1(input_text):
    # Task 1 logic
    return "Task 1 Result: " + input_text

# Code for Task 2
def task2(input_image):
    # Task 2 logic
    return "Task 2 Result"

# interface one
iface1 = gr.Interface(
    fn=task1,
    inputs="text",
    outputs="text",
    title="Multi-Page Interface",
)
# interface two
iface2 = gr.Interface(
    fn=task2,
    inputs="image",
    outputs="text",
    title="Multi-Page Interface"
)

demo = gr.TabbedInterface([iface1, iface2], ["Text-to-text", "image-to-text"])

# Run the interface
demo.launch(share=False)