"""Interactive Dashboard for ContextScope Evaluation Results.

A beautiful, modern dashboard to visualize context quality metrics
and compare JSON vs Markdown format performance.

Usage:
    python dashboard.py
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient

# Color scheme - Modern, professional palette
COLORS = {
    'primary': '#6366f1',
    'secondary': '#8b5cf6',
    'success': '#10b981',
    'warning': '#f59e0b',
    'danger': '#ef4444',
    'json': '#3b82f6',
    'markdown': '#8b5cf6',
    'background': '#0f172a',
    'surface': '#1e293b',
    'text': '#f1f5f9',
    'text_secondary': '#94a3b8',
    'grid': '#334155',
}


class EvaluationDataService:
    """Service to load and aggregate evaluation data from MongoDB."""
    
    def __init__(self, mongo_client: MongoDBClient):
        self.db = mongo_client.database
        self.collection = self.db["full_results"]
    
    def get_all_evaluations(self) -> List[Dict]:
        return list(self.collection.find().sort("evaluation_timestamp", -1))
    
    def get_evaluation_by_id(self, eval_id: str) -> Optional[Dict]:
        from bson import ObjectId
        return self.collection.find_one({"_id": ObjectId(eval_id)})
    
    def get_evaluations_by_user(self, user_email: str) -> List[Dict]:
        return list(self.collection.find({"user_email": user_email}).sort("evaluation_timestamp", -1))
    
    def get_unique_users(self) -> List[str]:
        return self.collection.distinct("user_email")
    
    def get_aggregated_metrics(self, user_email: Optional[str] = None) -> Dict:
        match_stage = {"user_email": user_email} if user_email else {}
        
        pipeline = [
            {"$match": match_stage},
            {
                "$group": {
                    "_id": None,
                    "total_evaluations": {"$sum": 1},
                    "avg_json_quality": {"$avg": "$json_pipeline.summary.end_to_end_quality"},
                    "avg_md_quality": {"$avg": "$markdown_pipeline.summary.end_to_end_quality"},
                    "avg_json_fidelity": {"$avg": "$json_pipeline.summary.avg_fidelity"},
                    "avg_md_fidelity": {"$avg": "$markdown_pipeline.summary.avg_fidelity"},
                    "avg_json_drift": {"$avg": "$json_pipeline.summary.avg_drift"},
                    "avg_md_drift": {"$avg": "$markdown_pipeline.summary.avg_drift"},
                    "avg_token_savings": {"$avg": "$comparison.token_savings_percent"},
                    "avg_quality_improvement": {"$avg": "$comparison.quality_improvement"},
                    "total_cost_saved": {"$sum": "$comparison.cost_savings_dollars"},
                }
            }
        ]
        
        result = list(self.collection.aggregate(pipeline))
        return result[0] if result else {}
    
    def get_latest_evaluation(self, user_email: Optional[str] = None) -> Optional[Dict]:
        query = {"user_email": user_email} if user_email else {}
        return self.collection.find_one(query, sort=[("evaluation_timestamp", -1)])


data_service: Optional[EvaluationDataService] = None


def create_metric_card(title: str, value: str, subtitle: str = "", 
                       color: str = COLORS['primary'], icon: str = "📊") -> html.Div:
    """Create a metric card component."""
    return html.Div([
        html.Div([
            html.Span(icon, style={'fontSize': '2rem', 'marginRight': '1rem'}),
            html.Div([
                html.H4(title, style={
                    'margin': '0',
                    'fontSize': '0.875rem',
                    'fontWeight': '500',
                    'color': COLORS['text_secondary'],
                    'textTransform': 'uppercase',
                    'letterSpacing': '0.05em'
                }),
                html.H2(value, style={
                    'margin': '0.5rem 0 0 0',
                    'fontSize': '2rem',
                    'fontWeight': '700',
                    'color': COLORS['text'],
                    'background': f'linear-gradient(135deg, {color} 0%, {COLORS["secondary"]} 100%)',
                    'WebkitBackgroundClip': 'text',
                    'WebkitTextFillColor': 'transparent',
                }),
                html.P(subtitle, style={
                    'margin': '0.25rem 0 0 0',
                    'fontSize': '0.875rem',
                    'color': COLORS['text_secondary']
                }) if subtitle else None
            ], style={'flex': '1'})
        ], style={
            'display': 'flex',
            'alignItems': 'center'
        })
    ], style={
        'background': COLORS['surface'],
        'borderRadius': '1rem',
        'padding': '1.5rem',
        'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
        'border': f'1px solid {COLORS["grid"]}',
        'transition': 'transform 0.2s, box-shadow 0.2s',
    }, className='metric-card')


def create_pipeline_flow_chart(data: Dict) -> go.Figure:
    """Create a Sankey-style pipeline flow chart showing stage-to-stage transitions."""
    
    json_handoffs = data['json_pipeline']['handoffs']
    md_handoffs = data['markdown_pipeline']['handoffs']
    
    # Extract stages
    stages = []
    for h in json_handoffs:
        if h['from'] not in stages:
            stages.append(h['from'])
        if h['to'] not in stages:
            stages.append(h['to'])
    
    # Create subplots for each handoff
    num_handoffs = len(json_handoffs)
    fig = make_subplots(
        rows=1, cols=num_handoffs,
        subplot_titles=[f"<b>{h['from'].split()[-1]}</b><br>↓<br><b>{h['to'].split()[-1]}</b>" 
                       for h in json_handoffs],
        specs=[[{'type': 'bar'}] * num_handoffs],
        horizontal_spacing=0.08
    )
    
    # Add bars for each handoff
    for idx, (json_h, md_h) in enumerate(zip(json_handoffs, md_handoffs), 1):
        # Fidelity bars
        fig.add_trace(
            go.Bar(
                name='JSON Fidelity' if idx == 1 else None,
                x=['Fidelity'],
                y=[json_h.get('fidelity', 0)],
                marker=dict(color=COLORS['json'], opacity=0.8),
                text=[f"{json_h.get('fidelity', 0):.2f}"],
                textposition='inside',
                textfont=dict(color='white', size=14, weight='bold'),
                showlegend=(idx == 1),
                legendgroup='json',
                hovertemplate=f'<b>JSON</b><br>Fidelity: %{{y:.3f}}<extra></extra>',
            ),
            row=1, col=idx
        )
        
        fig.add_trace(
            go.Bar(
                name='Markdown Fidelity' if idx == 1 else None,
                x=['Fidelity'],
                y=[md_h.get('fidelity', 0)],
                marker=dict(color=COLORS['markdown'], opacity=0.8),
                text=[f"{md_h.get('fidelity', 0):.2f}"],
                textposition='inside',
                textfont=dict(color='white', size=14, weight='bold'),
                showlegend=(idx == 1),
                legendgroup='markdown',
                hovertemplate=f'<b>Markdown</b><br>Fidelity: %{{y:.3f}}<extra></extra>',
            ),
            row=1, col=idx
        )
        
        # Drift bars (inverted for better visualization - lower is better)
        fig.add_trace(
            go.Bar(
                name='JSON Drift' if idx == 1 else None,
                x=['Drift'],
                y=[1 - json_h.get('drift', 0)],  # Inverted
                marker=dict(
                    color=COLORS['json'],
                    opacity=0.5,
                    line=dict(color=COLORS['json'], width=2)  # Removed dash property
                ),
                text=[f"{json_h.get('drift', 0):.2f}"],
                textposition='inside',
                textfont=dict(color='white', size=12),
                showlegend=(idx == 1),
                legendgroup='json',
                hovertemplate=f'<b>JSON</b><br>Drift: {json_h.get("drift", 0):.3f}<extra></extra>',
            ),
            row=1, col=idx
        )
        
        fig.add_trace(
            go.Bar(
                name='Markdown Drift' if idx == 1 else None,
                x=['Drift'],
                y=[1 - md_h.get('drift', 0)],  # Inverted
                marker=dict(
                    color=COLORS['markdown'],
                    opacity=0.5,
                    line=dict(color=COLORS['markdown'], width=2)  # Removed dash property
                ),
                text=[f"{md_h.get('drift', 0):.2f}"],
                textposition='inside',
                textfont=dict(color='white', size=12),
                showlegend=(idx == 1),
                legendgroup='markdown',
                hovertemplate=f'<b>Markdown</b><br>Drift: {md_h.get("drift", 0):.3f}<extra></extra>',
            ),
            row=1, col=idx
        )
    
    fig.update_layout(
        height=550,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['surface'],
        font=dict(color=COLORS['text'], size=11),
        barmode='group',
        bargap=0.15,
        bargroupgap=0.05,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
        ),
        margin=dict(t=100, b=90, l=40, r=40),
        hoverlabel=dict(
            bgcolor=COLORS['surface'],
            font_size=12,
        ),
    )
    
    # Update all xaxes and yaxes
    for i in range(1, num_handoffs + 1):
        fig.update_xaxes(
            showgrid=False,
            tickfont=dict(size=10, color=COLORS['text_secondary']),
            row=1, col=i
        )
        fig.update_yaxes(
            gridcolor=COLORS['grid'],
            showgrid=True,
            range=[0, 1.1],
            tickfont=dict(size=10, color=COLORS['text_secondary']),
            title_text="Score" if i == 1 else None,
            row=1, col=i
        )
    
    # Style subplot titles
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(size=13, color=COLORS['text'])
        annotation['y'] = annotation['y'] + 0.02
    
    return fig


def create_quality_progression_chart(data: Dict) -> go.Figure:
    """Create a line chart showing quality progression through the pipeline."""
    
    json_handoffs = data['json_pipeline']['handoffs']
    md_handoffs = data['markdown_pipeline']['handoffs']
    
    # Calculate cumulative quality (fidelity * (1 - drift))
    stages = ['Start'] + [h['to'].split()[-1] for h in json_handoffs]
    
    json_quality = [1.0]  # Start at 100%
    md_quality = [1.0]
    
    for json_h, md_h in zip(json_handoffs, md_handoffs):
        json_q = json_h.get('fidelity', 0) * (1 - json_h.get('drift', 0))
        md_q = md_h.get('fidelity', 0) * (1 - md_h.get('drift', 0))
        
        json_quality.append(json_quality[-1] * json_q)
        md_quality.append(md_quality[-1] * md_q)
    
    fig = go.Figure()
    
    # JSON line
    fig.add_trace(go.Scatter(
        name='JSON Quality Path',
        x=stages,
        y=json_quality,
        mode='lines+markers+text',
        line=dict(color=COLORS['json'], width=4),
        marker=dict(size=12, color=COLORS['json'], line=dict(color='white', width=2)),
        text=[f"{q:.1%}" for q in json_quality],
        textposition='top center',
        textfont=dict(size=11, color=COLORS['json'], weight='bold'),
        hovertemplate='<b>JSON</b><br>Stage: %{x}<br>Quality: %{y:.2%}<extra></extra>',
    ))
    
    # Markdown line
    fig.add_trace(go.Scatter(
        name='Markdown Quality Path',
        x=stages,
        y=md_quality,
        mode='lines+markers+text',
        line=dict(color=COLORS['markdown'], width=4),
        marker=dict(size=12, color=COLORS['markdown'], line=dict(color='white', width=2)),
        text=[f"{q:.1%}" for q in md_quality],
        textposition='bottom center',
        textfont=dict(size=11, color=COLORS['markdown'], weight='bold'),
        hovertemplate='<b>Markdown</b><br>Stage: %{x}<br>Quality: %{y:.2%}<extra></extra>',
    ))
    
    # Add shaded area between lines
    fig.add_trace(go.Scatter(
        x=stages + stages[::-1],
        y=json_quality + md_quality[::-1],
        fill='toself',
        fillcolor='rgba(139, 92, 246, 0.1)',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip',
    ))
    
    fig.update_layout(
        title=dict(
            text='<b>Information Quality Through Pipeline</b><br><sub>Higher is better - shows cumulative information preservation</sub>',
            font=dict(size=18, color=COLORS['text']),
            x=0.5, xanchor='center'
        ),
        height=400,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['surface'],
        font=dict(color=COLORS['text']),
        xaxis=dict(
            title='<b>Pipeline Stage</b>',
            gridcolor=COLORS['grid'],
            showgrid=True,
            tickfont=dict(size=12, color=COLORS['text']),
        ),
        yaxis=dict(
            title='<b>Cumulative Quality</b>',
            gridcolor=COLORS['grid'],
            showgrid=True,
            tickformat='.0%',
            range=[0, 1.1],
            tickfont=dict(size=11, color=COLORS['text_secondary']),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(0,0,0,0)',
            font=dict(size=13),
        ),
        margin=dict(t=100, b=90, l=70, r=40),
        hovermode='x unified',
    )
    
    return fig


def create_token_efficiency_chart(data: Dict) -> go.Figure:
    """Create token usage comparison chart."""
    
    json_handoffs = data['json_pipeline']['handoffs']
    md_handoffs = data['markdown_pipeline']['handoffs']
    
    stages = [h['from'].split()[-1] for h in json_handoffs]
    json_tokens = [h['tokens_sent'] for h in json_handoffs]
    md_tokens = [h['tokens_sent'] for h in md_handoffs]
    savings_pct = [(j - m) / j * 100 if j > 0 else 0 for j, m in zip(json_tokens, md_tokens)]
    
    fig = go.Figure()
    
    # JSON bars
    fig.add_trace(go.Bar(
        name='JSON Tokens',
        x=stages,
        y=json_tokens,
        marker=dict(color=COLORS['json'], opacity=0.8),
        text=[f"<b>{t:,}</b>" for t in json_tokens],
        textposition='outside',
        textfont=dict(size=11, color=COLORS['json']),
        hovertemplate='<b>JSON</b><br>Tokens: %{y:,}<extra></extra>',
    ))
    
    # Markdown bars
    fig.add_trace(go.Bar(
        name='Markdown Tokens',
        x=stages,
        y=md_tokens,
        marker=dict(color=COLORS['markdown'], opacity=0.8),
        text=[f"<b>{t:,}</b>" for t in md_tokens],
        textposition='outside',
        textfont=dict(size=11, color=COLORS['markdown']),
        hovertemplate='<b>Markdown</b><br>Tokens: %{y:,}<extra></extra>',
    ))
    
    # Savings line
    fig.add_trace(go.Scatter(
        name='Token Savings %',
        x=stages,
        y=[max(max(json_tokens), max(md_tokens)) * 0.85] * len(stages),
        mode='markers+text',
        marker=dict(size=0.1, opacity=0),
        text=[f"<b>-{s:.0f}%</b>" for s in savings_pct],
        textfont=dict(size=13, color=COLORS['success'], family='monospace'),
        showlegend=False,
        hoverinfo='skip',
    ))
    
    fig.update_layout(
        title=dict(
            text='<b>Token Usage by Pipeline Stage</b>',
            font=dict(size=18, color=COLORS['text'])
        ),
        height=400,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['surface'],
        font=dict(color=COLORS['text']),
        barmode='group',
        bargap=0.2,
        bargroupgap=0.1,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(0,0,0,0)',
        ),
        xaxis=dict(
            title='<b>Agent Stage</b>',
            gridcolor=COLORS['grid'],
            showgrid=False,
            tickfont=dict(size=12, color=COLORS['text']),
        ),
        yaxis=dict(
            title='<b>Tokens Sent</b>',
            gridcolor=COLORS['grid'],
            showgrid=True,
            tickfont=dict(size=11, color=COLORS['text_secondary']),
        ),
        margin=dict(t=80, b=90, l=70, r=40),
    )
    
    return fig


def create_cost_savings_gauge(data: Dict) -> go.Figure:
    """Create gauge chart showing cost savings."""
    
    json_tokens = sum(h['tokens_sent'] for h in data['json_pipeline']['handoffs'])
    md_tokens = sum(h['tokens_sent'] for h in data['markdown_pipeline']['handoffs'])
    
    savings_pct = ((json_tokens - md_tokens) / json_tokens * 100) if json_tokens > 0 else 0
    
    cost_per_million = 0.50
    json_cost = (json_tokens / 1_000_000) * cost_per_million
    md_cost = (md_tokens / 1_000_000) * cost_per_million
    cost_savings = json_cost - md_cost
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=savings_pct,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={
            'text': f"<b>Token Savings</b><br><sub>${cost_savings:.4f} saved per run</sub>",
            'font': {'size': 18, 'color': COLORS['text']}
        },
        delta={
            'reference': 50,
            'increasing': {'color': COLORS['success']},
            'suffix': '%'
        },
        number={
            'suffix': '%',
            'font': {'size': 42, 'color': COLORS['text'], 'family': 'monospace'}
        },
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickcolor': COLORS['text']
            },
            'bar': {'color': COLORS['success']},
            'bgcolor': COLORS['background'],
            'borderwidth': 2,
            'bordercolor': COLORS['grid'],
            'steps': [
                {'range': [0, 33], 'color': 'rgba(239, 68, 68, 0.3)'},
                {'range': [33, 66], 'color': 'rgba(245, 158, 11, 0.3)'},
                {'range': [66, 100], 'color': 'rgba(16, 185, 129, 0.3)'}
            ],
            'threshold': {
                'line': {'color': COLORS['text'], 'width': 4},
                'thickness': 0.75,
                'value': savings_pct
            }
        }
    ))
    
    fig.update_layout(
        height=320,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['surface'],
        font=dict(color=COLORS['text']),
        margin=dict(t=90, b=20, l=20, r=20),
    )
    
    return fig


def create_recommendations_table(data: Dict) -> html.Div:
    """Create comparison table for final recommendations."""
    
    json_recs = data['json_pipeline']['final_recommendations']
    md_recs = data['markdown_pipeline']['final_recommendations']
    
    rows = []
    for i in range(min(5, len(json_recs), len(md_recs))):
        json_rec = json_recs[i]
        md_rec = md_recs[i]
        
        match = json_rec['title'] == md_rec['title']
        
        rows.append(html.Tr([
            html.Td(str(i + 1), style={'textAlign': 'center', 'fontWeight': 'bold', 'width': '60px'}),
            html.Td([
                html.Div(json_rec['title'], style={'fontWeight': '500', 'marginBottom': '0.25rem'}),
                html.Div(f"({json_rec['year']})", style={
                    'fontSize': '0.8rem',
                    'color': COLORS['text_secondary']
                })
            ], style={'padding': '0.75rem'}),
            html.Td([
                html.Div(md_rec['title'], style={'fontWeight': '500', 'marginBottom': '0.25rem'}),
                html.Div(f"({md_rec['year']})", style={
                    'fontSize': '0.8rem',
                    'color': COLORS['text_secondary']
                })
            ], style={'padding': '0.75rem'}),
            html.Td(
                '✓' if match else '✗',
                style={
                    'textAlign': 'center',
                    'fontSize': '1.5rem',
                    'fontWeight': 'bold',
                    'color': COLORS['success'] if match else COLORS['danger'],
                    'width': '80px'
                }
            )
        ], style={
            'borderBottom': f'1px solid {COLORS["grid"]}',
            'transition': 'background-color 0.2s',
        }, className='table-row'))
    
    return html.Div([
        html.Table([
            html.Thead(html.Tr([
                html.Th('#', style={'textAlign': 'center', 'width': '60px'}),
                html.Th('JSON Pipeline'),
                html.Th('Markdown Pipeline'),
                html.Th('Match', style={'textAlign': 'center', 'width': '80px'}),
            ], style={
                'borderBottom': f'2px solid {COLORS["primary"]}',
                'color': COLORS['text'],
                'textTransform': 'uppercase',
                'fontSize': '0.75rem',
                'letterSpacing': '0.1em',
                'fontWeight': '600',
                'padding': '1rem 0.75rem',
            })),
            html.Tbody(rows)
        ], style={
            'width': '100%',
            'borderCollapse': 'collapse',
            'color': COLORS['text'],
        })
    ], style={
        'background': COLORS['surface'],
        'borderRadius': '1rem',
        'padding': '1.5rem',
        'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
        'border': f'1px solid {COLORS["grid"]}',
    })


def create_dashboard() -> dash.Dash:
    """Create the main dashboard application."""
    
    app = dash.Dash(__name__, title="ContextScope Evaluation Dashboard")
    
    # Get initial data
    users = data_service.get_unique_users()
    latest_eval = data_service.get_latest_evaluation()
    agg_metrics = data_service.get_aggregated_metrics()
    
    # Create user dropdown options
    user_options = [{'label': '📊 All Users (Aggregated)', 'value': 'all'}]
    user_options.extend([{'label': f'👤 {user}', 'value': user} for user in users])
    
    app.layout = html.Div([
        # Store for current evaluation data
        dcc.Store(id='current-evaluation'),
        
        # Header
        html.Div([
            html.Div([
                html.H1([
                    html.Span('🔬 ', style={'marginRight': '0.5rem'}),
                    'ContextScope Evaluation Dashboard'
                ], style={
                    'margin': '0',
                    'fontSize': '2.5rem',
                    'fontWeight': '800',
                    'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                    'WebkitBackgroundClip': 'text',
                    'WebkitTextFillColor': 'transparent',
                }),
                html.P(
                    f'JSON vs Markdown Context Format Comparison • Total Evaluations: {agg_metrics.get("total_evaluations", 0)}',
                    style={
                        'margin': '0.5rem 0 0 0',
                        'fontSize': '1rem',
                        'color': COLORS['text_secondary']
                    }
                )
            ], style={'flex': '1'}),
        ], style={
            'background': COLORS['surface'],
            'padding': '2rem',
            'marginBottom': '2rem',
            'borderRadius': '1rem',
            'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
            'border': f'1px solid {COLORS["grid"]}',
        }),
        
        # User Selection
        html.Div([
            html.Label('Select View:', style={
                'color': COLORS['text'],
                'fontSize': '1rem',
                'fontWeight': '600',
                'marginBottom': '0.75rem',
                'display': 'block'
            }),
            dcc.Dropdown(
                id='user-selector',
                options=user_options,
                value='all',
                style={'marginBottom': '0.75rem'},
                className='custom-dropdown'
            ),
            html.Div(id='user-info', style={
                'color': COLORS['text_secondary'],
                'fontSize': '0.875rem',
                'fontStyle': 'italic'
            })
        ], style={
            'background': COLORS['surface'],
            'padding': '1.5rem',
            'marginBottom': '2rem',
            'borderRadius': '1rem',
            'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
            'border': f'1px solid {COLORS["grid"]}',
        }),
        
        # Dynamic content container
        html.Div(id='dashboard-content')
        
    ], style={
        'maxWidth': '1600px',
        'margin': '0 auto',
        'padding': '2rem',
        'background': COLORS['background'],
        'minHeight': '100vh',
        'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    })
    
    # Custom CSS
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background: ''' + COLORS['background'] + ''';
                }
                
                .metric-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 12px 20px -3px rgba(0, 0, 0, 0.5) !important;
                }
                
                .table-row:hover {
                    background-color: ''' + COLORS['grid'] + '''40 !important;
                }
                
                /* Dropdown styling */
                .Select-control {
                    background-color: ''' + COLORS['background'] + ''' !important;
                    border-color: ''' + COLORS['grid'] + ''' !important;
                    border-radius: 0.5rem !important;
                }
                
                .Select-menu-outer {
                    background-color: ''' + COLORS['surface'] + ''' !important;
                    border-color: ''' + COLORS['grid'] + ''' !important;
                    border-radius: 0.5rem !important;
                }
                
                .Select-option {
                    background-color: ''' + COLORS['surface'] + ''' !important;
                    color: ''' + COLORS['text'] + ''' !important;
                }
                
                .Select-option:hover {
                    background-color: ''' + COLORS['grid'] + ''' !important;
                }
                
                /* Scrollbar styling */
                ::-webkit-scrollbar {
                    width: 12px;
                    height: 12px;
                }
                
                ::-webkit-scrollbar-track {
                    background: ''' + COLORS['background'] + ''';
                }
                
                ::-webkit-scrollbar-thumb {
                    background: ''' + COLORS['grid'] + ''';
                    border-radius: 6px;
                }
                
                ::-webkit-scrollbar-thumb:hover {
                    background: ''' + COLORS['text_secondary'] + ''';
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''
    
    # Callback to update dashboard
    @app.callback(
        [Output('dashboard-content', 'children'),
         Output('user-info', 'children')],
        [Input('user-selector', 'value')]
    )
    def update_dashboard(selected_user):
        if selected_user == 'all':
            agg_data = data_service.get_aggregated_metrics()
            latest = data_service.get_latest_evaluation()
            
            if not latest:
                return html.Div("No evaluation data available", style={'color': COLORS['text']}), ""
            
            data = latest
            info_text = f"📊 Showing aggregated metrics across {agg_data.get('total_evaluations', 0)} evaluations"
            
        else:
            data = data_service.get_latest_evaluation(selected_user)
            
            if not data:
                return html.Div(f"No evaluation data for {selected_user}", style={'color': COLORS['text']}), ""
            
            user_evals = data_service.get_evaluations_by_user(selected_user)
            eval_date = data['evaluation_timestamp'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(data['evaluation_timestamp'], datetime) else str(data['evaluation_timestamp'])
            info_text = f"👤 Viewing {selected_user} • {len(user_evals)} total evaluations • Latest: {eval_date}"
        
        # Calculate metrics
        json_summary = data['json_pipeline']['summary']
        md_summary = data['markdown_pipeline']['summary']
        comparison = data.get('comparison', {})
        
        json_tokens = sum(h['tokens_sent'] for h in data['json_pipeline']['handoffs'])
        md_tokens = sum(h['tokens_sent'] for h in data['markdown_pipeline']['handoffs'])
        token_savings_pct = ((json_tokens - md_tokens) / json_tokens * 100) if json_tokens > 0 else 0
        
        json_titles = {r['title'] for r in data['json_pipeline']['final_recommendations']}
        md_titles = {r['title'] for r in data['markdown_pipeline']['final_recommendations']}
        overlap = len(json_titles & md_titles)
        
        content = html.Div([
            # Key Metrics Row
            html.Div([
                html.Div([
                    create_metric_card(
                        'JSON Quality',
                        f"{json_summary['end_to_end_quality']:.1%}",
                        f"Fidelity: {json_summary['avg_fidelity']:.2f} • Drift: {json_summary['avg_drift']:.2f}",
                        COLORS['json'],
                        '📘'
                    )
                ], style={'flex': '1', 'minWidth': '280px'}),
                
                html.Div([
                    create_metric_card(
                        'Markdown Quality',
                        f"{md_summary['end_to_end_quality']:.1%}",
                        f"Fidelity: {md_summary['avg_fidelity']:.2f} • Drift: {md_summary['avg_drift']:.2f}",
                        COLORS['markdown'],
                        '📝'
                    )
                ], style={'flex': '1', 'minWidth': '280px'}),
                
                html.Div([
                    create_metric_card(
                        'Token Savings',
                        f"{token_savings_pct:.0f}%",
                        f"{json_tokens - md_tokens:,} tokens saved",
                        COLORS['success'],
                        '💰'
                    )
                ], style={'flex': '1', 'minWidth': '280px'}),
                
                html.Div([
                    create_metric_card(
                        'Recommendation Match',
                        f"{overlap}/5",
                        f"{(overlap/5)*100:.0f}% overlap",
                        COLORS['warning'],
                        '🎯'
                    )
                ], style={'flex': '1', 'minWidth': '280px'}),
            ], style={
                'display': 'flex',
                'gap': '1.5rem',
                'marginBottom': '2rem',
                'flexWrap': 'wrap',
            }),
            
            # Pipeline Flow Chart
            html.Div([
                html.Div([
                    html.H3('📊 Pipeline Stage Analysis', style={
                        'margin': '0 0 1rem 0',
                        'fontSize': '1.25rem',
                        'fontWeight': '700',
                        'color': COLORS['text']
                    }),
                    dcc.Graph(
                        figure=create_pipeline_flow_chart(data),
                        config={'displayModeBar': False},
                    )
                ], style={
                    'background': COLORS['surface'],
                    'borderRadius': '1rem',
                    'padding': '1.5rem',
                    'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
                    'border': f'1px solid {COLORS["grid"]}',
                })
            ], style={'marginBottom': '2rem'}),
            
            # Quality Progression
            html.Div([
                html.Div([
                    dcc.Graph(
                        figure=create_quality_progression_chart(data),
                        config={'displayModeBar': False}
                    )
                ], style={
                    'background': COLORS['surface'],
                    'borderRadius': '1rem',
                    'padding': '1.5rem',
                    'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
                    'border': f'1px solid {COLORS["grid"]}',
                })
            ], style={'marginBottom': '2rem'}),
            
            # Token Efficiency & Cost Savings
            html.Div([
                html.Div([
                    dcc.Graph(
                        figure=create_token_efficiency_chart(data),
                        config={'displayModeBar': False}
                    )
                ], style={
                    'flex': '2',
                    'background': COLORS['surface'],
                    'borderRadius': '1rem',
                    'padding': '1.5rem',
                    'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
                    'border': f'1px solid {COLORS["grid"]}',
                }),
                
                html.Div([
                    dcc.Graph(
                        figure=create_cost_savings_gauge(data),
                        config={'displayModeBar': False}
                    )
                ], style={
                    'flex': '1',
                    'background': COLORS['surface'],
                    'borderRadius': '1rem',
                    'padding': '1.5rem',
                    'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
                    'border': f'1px solid {COLORS["grid"]}',
                    'minWidth': '300px',
                })
            ], style={
                'display': 'flex',
                'gap': '1.5rem',
                'marginBottom': '2rem',
                'flexWrap': 'wrap',
            }),
            
            # Recommendations Table
            html.Div([
                html.H2('🎬 Final Recommendations Comparison', style={
                    'margin': '0 0 1.5rem 0',
                    'fontSize': '1.5rem',
                    'fontWeight': '700',
                    'color': COLORS['text']
                }),
                create_recommendations_table(data)
            ], style={'marginBottom': '2rem'}),
            
            # Footer Insight
            html.Div([
                html.P([
                    '💡 ',
                    html.Strong('Key Insight: ', style={'fontSize': '1.05rem'}),
                    f"Markdown format achieves {100 - abs(comparison.get('quality_improvement', 0)) * 100:.0f}% similar quality ",
                    f"with {token_savings_pct:.0f}% fewer tokens, resulting in ",
                    html.Strong(f"${comparison.get('cost_savings_dollars', 0):.4f} cost savings ", style={'color': COLORS['success']}),
                    "and faster processing per run."
                ], style={
                    'margin': '0',
                    'fontSize': '1rem',
                    'color': COLORS['text'],
                    'textAlign': 'center',
                    'lineHeight': '1.6'
                })
            ], style={
                'background': f'linear-gradient(135deg, {COLORS["primary"]}25 0%, {COLORS["secondary"]}15 100%)',
                'padding': '2rem',
                'borderRadius': '1rem',
                'border': f'2px solid {COLORS["primary"]}40',
                'boxShadow': f'0 0 30px {COLORS["primary"]}20',
            })
        ])
        
        return content, info_text
    
    return app


def main():
    """Main entry point."""
    global data_service
    
    try:
        print("Connecting to MongoDB...")
        settings = get_settings()
        client = MongoDBClient(settings)
        data_service = EvaluationDataService(client)
        
        all_evals = data_service.get_all_evaluations()
        if not all_evals:
            print("\n" + "="*70)
            print("⚠️  No evaluation data found in MongoDB!")
            print("="*70)
            print("\nPlease run demo_context_evaluation.py first to generate evaluation data.")
            print("\nExample:")
            print("  python demo_context_evaluation.py")
            sys.exit(1)
        
        print(f"✓ Found {len(all_evals)} evaluations in database")
        
        print("Creating dashboard...")
        app = create_dashboard()
        
        print("\n" + "="*70)
        print("🚀 ContextScope Dashboard Running!")
        print("="*70)
        print(f"\n📊 Found {len(data_service.get_unique_users())} unique users")
        print(f"📈 Total evaluations: {len(all_evals)}")
        print("\n🌐 Open your browser: http://127.0.0.1:8050")
        print("\n💡 Features:")
        print("   • Stage-by-stage pipeline analysis")
        print("   • Quality progression tracking")
        print("   • Token efficiency comparison")
        print("   • Per-user and aggregated views")
        print("\n⌨️  Press Ctrl+C to stop\n")
        
        app.run(debug=True, host='127.0.0.1', port=8050)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()