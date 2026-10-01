import re

with open('site/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'(<canvas[^>]*></canvas>)', r'<div class="chart-wrapper">\1</div>', text)

# Update cache buster to force css and css styles reload if needed, but we already updated app.js. 
# Let's also update the app.js timestamp just in case.
text = text.replace('app.js?v=3', 'app.js?v=4')

with open('site/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

with open('site/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

if 'display:flex;flex-direction:column' not in css:
    css = css.replace('.card{background:', '.card{display:flex;flex-direction:column;background:')

if '.chart-wrapper' not in css:
    css += '\n.chart-wrapper { position: relative; flex: 1; min-height: 230px; width: 100%; margin-top: 10px; }\n'

with open('site/styles.css', 'w', encoding='utf-8') as f:
    f.write(css)
