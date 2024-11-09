import dash
import pandas as pd
from dash import html
from dash import dcc
import cdata as mod
import pymongo
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots


app = dash.Dash(__name__)
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["InvoiceDB"]
products = db["products"]
suppliers = db["suppliers"]
invoices = db["invoices"]
customers = db["customers"]
data = list(products.find({}))
items = [item['description'] for item in data]
price = [item['unitPrice'] for item in data]

fig = go.Figure()
fig.add_trace(go.Bar(x=items, y=price))

fig.update_layout(title='Price for Each Product', xaxis=dict(title='Item'), yaxis=dict(title='Price'))

app.layout = html.Div([
    html.Label("Select items to display:"),
    dcc.Dropdown(
        id="item-dropdown",
        options=[{'label': item, 'value': item} for item in items],
        multi=True,
        value=items  # Pre-select all items initially
    ),
    dcc.Graph(figure=fig, id='item-price-graph')
])

@app.callback(
    dash.dependencies.Output('item-price-graph', 'figure'),
    [dash.dependencies.Input('item-dropdown', 'value')]
)

def update_graph(selected_items):
    if not selected_items:
        # If no items selected, display an empty graph
        return {
            'data': [],
            'layout': {
                'title': 'Price for Each Product',
                'xaxis': {'title': 'Item'},
                'yaxis': {'title': 'Price'}
            }
        }
    
    filtered_items = [item for item in data if item['description'] in selected_items]
    filtered_prices = [item['unitPrice'] for item in filtered_items]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=selected_items, y=filtered_prices))

    fig.update_layout(title='Price for Selected Products', xaxis=dict(title='Item'), yaxis=dict(title='Price'))
    return fig

if __name__ == '__main__':
    app.run(debug=True)