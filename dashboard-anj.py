# -*- coding: utf-8 -*-

import dash
# from dash import dash_table
from dash import dcc
from dash import html
# import dash_daq as daq
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

external_stylesheets = [dbc.themes.BOOTSTRAP, 'https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

print('Loading data')
df = pd.read_csv(
    'https://static.data.gouv.fr/resources/donnees-sur-le-marche-des-jeux-en-ligne-paris-sportifs-hippiques-et-poker-de-2010-a-2022/20230921-134726/anj-donnees-marche-jeux-en-ligne-20102022.csv',
    encoding="cp1252",
    sep=";"
)
df.columns = [c.replace('Au ', '') for c in df.columns]
df = df.loc[~df['Catégorie/Année'].isna()]
# pour différencier Part mises origine VS sport
for c in df.columns:
    df['Catégorie/Année'] = df['Catégorie/Année'].apply(
        lambda x: x.replace('Part mises', 'Part des mises sur')
        if 'T4' in x and 'Part mises' in x
        else "Nombre total d'agréments" if x == "Nombre d’agréments"
        else x
    )
    df['Catégorie/Année'] = df['Catégorie/Année'].apply(
        lambda x: (
            x.replace('PS T4', 'Paris sportifs')
            .replace('PO T4', 'Poker')
            .replace('PH T4', 'Paris hippiques')
            .replace('de comptes joueurs actifs', 'CJA')
        )
    )
df = df.set_index('Catégorie/Année')
df = df.rename_axis('Catégorie')
for c in df.columns:
    df[c] = df[c].apply(
        lambda x: int(x.replace('%', '').replace(' ', ''))
        if isinstance(x, str) else x
    )

types = {
    "agréments": "Nombre d'agréments",
    "Nombre CJA": "Nombre de comptes joueurs actifs",
    "Mises": "Mises totales annuelles (en M€)",
    "smartphones": "Part de mises sur smartphones et tablettes (en %)",
    "Part femmes": "Part de mises faites par des femmes (en %)",
    "PBJ": "Produit but des jeux (chiffre d'affaires, en M€)",
    "Part mises": "Part des mises par sport (en %)",
    "marketing": "Budget marketing médias (en M€)",
}


def insert_line_breaks(input_string, max_length=30):
    words = input_string.split()
    lines = []
    current_line = []

    for word in words:
        if len(' '.join(current_line + [word])) <= max_length:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return '<br>'.join(lines)


# %% APP LAYOUT:
app.layout = dbc.Container(
    [
        dbc.Row([
            html.H3("Evolution des pratiques de jeux d'argent",
                    style={
                        "padding": "5px 0px 10px 0px",  # "padding": "top right down left"
                    }),
        ]),
        dbc.Row([
            html.H5('Données à visualiser'),
            dcc.Dropdown(
                id='types_dropdown',
                placeholder="Quel type de données recherchez-vous ?",
                searchable=True,
                multi=True,
                options=[
                    {'label': l, 'value': v} for (v, l) in types.items()
                ],
            ),
        ],
            style={"padding": "0px 0px 5px 0px"},
        ),
        dbc.Row([
            dbc.Alert(
                id="only_two_alert",
                children="Le graphe ne peut afficher plus de 2 types à la fois.",
                color="danger",
                is_open=False,
                dismissable=True,
            )
        ],
            style={"padding": "0px 0px 5px 0px"},
        ),
        dbc.Row([
            dcc.Markdown(id="context_markdown")
        ],
            style={"padding": "0px 0px 0px 0px"},
        ),
        dbc.Row([
            dcc.Graph(
                id='graph',
            )
        ],
            style={"padding": "0px 0px 10px 0px"},
        ),
        dbc.Row([
            dcc.Markdown(
                "Source des données : [Données ouvertes de l'ANJ sur data.gouv.fr]"
                + "(https://www.data.gouv.fr/fr/datasets/63b6f3c260d1fc5d875f864e/)"
            )
        ],
            style={"padding": "0px 0px 0px 0px"},
        ),
    ])

# %% Callbacks


@app.callback(
    Output('graph', 'figure'),
    [Input('types_dropdown', 'value')]
)
def update_graph(params):
    if not params or len(params) > 2:
        raise PreventUpdate

    if len(params) == 1:
        param = params[0]
        to_plot = df.loc[df.index.str.contains(param)].T
        to_plot.columns = [
            insert_line_breaks(c) for c in to_plot.columns
        ]
        figure = px.line(
            to_plot,
            x=to_plot.index,
            y=to_plot.columns,
            title=types[param]
        )
        if "%" in types[param]:
            figure.update_yaxes(
                range=[0, round(np.nanmax(to_plot.values)*1.1)]
            )
        figure.update_layout(
            xaxis_title='Date de relevé',
            yaxis_title='',
            legend_title_text='Légende'
        )
    else:
        figure = make_subplots(specs=[[{"secondary_y": True}]])
        for idx, p in enumerate(params):
            to_plot = df.loc[df.index.str.contains(p)]
            to_plot.index = [
                insert_line_breaks(c) for c in to_plot.index
            ]
            for i in to_plot.index:
                figure.add_trace(
                    go.Scatter(
                        x=to_plot.columns,
                        y=to_plot.loc[i],
                        name=i,
                        mode="lines"
                    ),
                    secondary_y=idx == 1
                )
        figure.update_xaxes(title_text="Date de relevé")
        # adapt y-axies ranges?
        figure.update_yaxes(title_text=types[params[0]], secondary_y=False)
        figure.update_yaxes(title_text=types[params[1]], secondary_y=True)
        figure.update_layout(
            title=types[params[0]] + ' VS ' + types[params[1]],
            legend_title_text='Légende'
        )
    return figure


@app.callback(
    [
        Output('context_markdown', 'children'),
        Output('only_two_alert', 'is_open')
    ],
    [Input('types_dropdown', 'value')]
)
def update_context(params):
    if not params:
        raise PreventUpdate
    context = "> "
    for idx, p in enumerate(params):
        if p == "agréments":
            context += (
                "Nombre d'entités ayant l'[agrément ANJ]"
                "(https://anj.fr/offre-de-jeu-et-marche/operateurs-agrees),"
                " pour chaque type."
            )
        elif p == "Nombre CJA":
            context += (
                "Nombre de comptes joueurs actifs à date,"
                " pour chaque type."
            )
        elif p == "Mises":
            context += (
                "Mises annuelles des joueurs en millions d'euros,"
                " pour chaque type."
            )
        elif p == "smartphones":
            context += (
                "Pourcentage de mises faites sur smartphones et tablettes"
                " (par opposition aux mises effectuées sur ordinateurs)"
                " sur l'année, pour chaque type."
            )
        elif p == "Part femmes":
            context += (
                "Pourcentage de mises faites par des femmes sur l'année,"
                " pour chaque type."
            )
        elif p == "PBJ":
            context += (
                "Produit brut des jeux sur l'année en millions d'euros,"
                " équivalent au chiffre d'affaires des entreprises,"
                " pour chaque type."
            )
        elif p == "Part mises":
            context += (
                "Pourcentage de mises par sport sur l'année"
                " (pour les sports les plus populaires)."
            )
        elif p == "Part mises":
            context += "Budget marketing médias annuel en millions d'euros."
        if idx < len(params) - 1:
            context += "\n\n> "
    return context, len(params) > 2


# %%
if __name__ == '__main__':
    app.run_server(debug=False, use_reloader=False, port=8051)
