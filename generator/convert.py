import jinja2
import os
import json

def generate_html():
    output = {}
    for subfolder in os.listdir("./generator"):
        if os.path.isdir(os.path.join("./generator", subfolder)):
            # read data.json as UTF-8 to preserve Slovenian characters
            # if data.json exists and template.html exists
            if not (os.path.exists(os.path.join("./generator", subfolder, "data.json")) and os.path.exists(os.path.join("./generator", subfolder, "template.html"))):
                continue

            with open(os.path.join("./generator", subfolder, "data.json"), encoding="utf-8") as f:
                data = json.load(f)
                files = os.listdir(os.path.join("./generator", subfolder))
                # ensure templates are read as UTF-8
                env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=os.path.join("./generator", subfolder), encoding="utf-8"))
                template = env.get_template("template.html")
            html = ''
            # If data requests full render, pass the whole data to template
            if isinstance(data, dict) and data.get('render') == 'full':
                rendered_html = template.render(data=data)
                html = rendered_html
            else:
                for datapoint in data['objs']:
                    rendered_html = template.render(datapoint)
                    html += rendered_html
            output[subfolder] = html
    return output

if __name__ == "__main__":
    # print unicode-safe JSON so console shows Slovenian characters correctly
    html = generate_html()

    for subfolder, content in html.items():
        print(f"Generated HTML for {subfolder}:")
        print(content)
        print()