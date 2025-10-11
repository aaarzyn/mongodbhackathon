"""Interactive Dashboard for ContextScope Evaluation Results.

A beautiful, modern dashboard to visualize context quality metrics
and compare JSON vs Markdown format performance.

Usage:
    python dashboard.py [path_to_evaluation_json]
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Color scheme - Modern, professional palette
COLORS = {
    'primary': '#6366f1',      # Indigo
    'secondary': '#8b5cf6',    # Purple
    'success': '#10b981',      # Green
    'warning': '#f59e0b',      # Amber
    'danger': '#ef4444',       # Red
    'json': '#3b82f6',         # Blue
    'markdown': '#8b5cf6',     # Purple
    'background': '#0f172a',   # Dark slate
    'surface': '#1e293b',      # Lighter slate
    'text': '#f1f5f9',         # Light slate
    'text_secondary': '#94a3b8', # Gray
    'grid': '#334155',         # Medium slate
}


def load_evaluation_data(filepath: str = "reports/context_evaluation.json") -> Dict:
    """Load evaluation results from JSON file.
    
    Args:
        filepath: Path to evaluation JSON file.
        
    Returns:
        Dictionary with evaluation data.
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def create_metric_card(title: str, value: str, subtitle: str = "", 
                       color: str = COLORS['primary'], icon: str = "📊") -> html.Div:
    """Create a metric card component.
    
    Args:
        title: Card title.
        value: Main metric value.
        subtitle: Optional subtitle.
        color: Accent color.
        icon: Emoji icon.
        
    Returns:
        Dash HTML div component.
    """
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


def create_fidelity_drift_chart(data: Dict) -> go.Figure:
    """Create combined fidelity and drift comparison chart.
    
    Args:
        data: Evaluation data.
        
    Returns:
        Plotly figure.
    """
    json_handoffs = data['json_pipeline']['handoffs']
    md_handoffs = data['markdown_pipeline']['handoffs']
    
    handoff_names = [f"{h['from'][:15]}... →\n{h['to'][:15]}..." for h in json_handoffs]
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Fidelity Score (Higher is Better)', 'Drift Score (Lower is Better)'),
        specs=[[{'type': 'bar'}, {'type': 'bar'}]]
    )
    
    # Fidelity comparison
    fig.add_trace(
        go.Bar(
            name='JSON',
            x=handoff_names,
            y=[h.get('fidelity', 0) for h in json_handoffs],
            marker=dict(
                color=COLORS['json'],
                line=dict(color=COLORS['json'], width=2)
            ),
            text=[f"{h.get('fidelity', 0):.2f}" for h in json_handoffs],
            textposition='outside',
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            name='Markdown',
            x=handoff_names,
            y=[h.get('fidelity', 0) for h in md_handoffs],
            marker=dict(
                color=COLORS['markdown'],
                line=dict(color=COLORS['markdown'], width=2)
            ),
            text=[f"{h.get('fidelity', 0):.2f}" for h in md_handoffs],
            textposition='outside',
        ),
        row=1, col=1
    )
    
    # Drift comparison
    fig.add_trace(
        go.Bar(
            name='JSON',
            x=handoff_names,
            y=[h.get('drift', 0) for h in json_handoffs],
            marker=dict(
                color=COLORS['json'],
                line=dict(color=COLORS['json'], width=2)
            ),
            text=[f"{h.get('drift', 0):.2f}" for h in json_handoffs],
            textposition='outside',
            showlegend=False
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Bar(
            name='Markdown',
            x=handoff_names,
            y=[h.get('drift', 0) for h in md_handoffs],
            marker=dict(
                color=COLORS['markdown'],
                line=dict(color=COLORS['markdown'], width=2)
            ),
            text=[f"{h.get('drift', 0):.2f}" for h in md_handoffs],
            textposition='outside',
            showlegend=False
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=500,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['surface'],
        font=dict(color=COLORS['text'], size=12),
        barmode='group',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(t=80, b=40, l=40, r=40),
    )
    
    fig.update_xaxes(
        gridcolor=COLORS['grid'],
        showgrid=True,
        tickangle=-45,
    )
    
    fig.update_yaxes(
        gridcolor=COLORS['grid'],
        showgrid=True,
        range=[0, 1.0],
    )
    
    return fig


def create_token_efficiency_chart(data: Dict) -> go.Figure:
    """Create token usage comparison waterfall chart.
    
    Args:
        data: Evaluation data.
        
    Returns:
        Plotly figure.
    """
    json_handoffs = data['json_pipeline']['handoffs']
    md_handoffs = data['markdown_pipeline']['handoffs']
    
    stages = [h['from'] for h in json_handoffs]
    json_tokens = [h['tokens_sent'] for h in json_handoffs]
    md_tokens = [h['tokens_sent'] for h in md_handoffs]
    savings = [j - m for j, m in zip(json_tokens, md_tokens)]
    savings_pct = [(j - m) / j * 100 if j > 0 else 0 for j, m in zip(json_tokens, md_tokens)]
    
    fig = go.Figure()
    
    # JSON tokens
    fig.add_trace(go.Bar(
        name='JSON Tokens',
        x=stages,
        y=json_tokens,
        marker=dict(color=COLORS['json']),
        text=[f"{t:,}" for t in json_tokens],
        textposition='outside',
    ))
    
    # Markdown tokens
    fig.add_trace(go.Bar(
        name='Markdown Tokens',
        x=stages,
        y=md_tokens,
        marker=dict(color=COLORS['markdown']),
        text=[f"{t:,}" for t in md_tokens],
        textposition='outside',
    ))
    
    # Savings overlay (as line)
    fig.add_trace(go.Scatter(
        name='Savings %',
        x=stages,
        y=[max(json_tokens) * 0.9] * len(stages),  # Position near top
        text=[f"-{s:.0f}%" for s in savings_pct],
        mode='text',
        textfont=dict(size=14, color=COLORS['success'], family='monospace'),
        showlegend=False,
    ))
    
    fig.update_layout(
        title=dict(
            text='Token Usage by Pipeline Stage',
            font=dict(size=20, color=COLORS['text'])
        ),
        height=400,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['surface'],
        font=dict(color=COLORS['text']),
        barmode='group',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0)',
        ),
        xaxis=dict(
            gridcolor=COLORS['grid'],
            showgrid=False,
        ),
        yaxis=dict(
            title='Tokens',
            gridcolor=COLORS['grid'],
            showgrid=True,
        ),
        margin=dict(t=80, b=40, l=60, r=40),
    )
    
    return fig


def create_quality_efficiency_scatter(data: Dict) -> go.Figure:
    """Create quality vs efficiency scatter plot.
    
    Args:
        data: Evaluation data.
        
    Returns:
        Plotly figure.
    """
    json_handoffs = data['json_pipeline']['handoffs']
    md_handoffs = data['markdown_pipeline']['handoffs']
    
    # Calculate efficiency (quality per 1k tokens)
    json_efficiency = [
        h.get('fidelity', 0) / (h['tokens_sent'] / 1000) if h['tokens_sent'] > 0 else 0
        for h in json_handoffs
    ]
    md_efficiency = [
        h.get('fidelity', 0) / (h['tokens_sent'] / 1000) if h['tokens_sent'] > 0 else 0
        for h in md_handoffs
    ]
    
    json_quality = [h.get('fidelity', 0) * (1 - h.get('drift', 0)) for h in json_handoffs]
    md_quality = [h.get('fidelity', 0) * (1 - h.get('drift', 0)) for h in md_handoffs]
    
    handoff_names = [h['from'] for h in json_handoffs]
    
    fig = go.Figure()
    
    # JSON points
    fig.add_trace(go.Scatter(
        x=json_efficiency,
        y=json_quality,
        mode='markers+text',
        name='JSON',
        marker=dict(
            size=15,
            color=COLORS['json'],
            line=dict(width=2, color='white'),
            symbol='circle'
        ),
        text=handoff_names,
        textposition='top center',
        textfont=dict(size=10, color=COLORS['text']),
    ))
    
    # Markdown points
    fig.add_trace(go.Scatter(
        x=md_efficiency,
        y=md_quality,
        mode='markers+text',
        name='Markdown',
        marker=dict(
            size=15,
            color=COLORS['markdown'],
            line=dict(width=2, color='white'),
            symbol='diamond'
        ),
        text=handoff_names,
        textposition='bottom center',
        textfont=dict(size=10, color=COLORS['text']),
    ))
    
    # Add diagonal reference line (better efficiency-quality trade-off)
    max_eff = max(max(json_efficiency), max(md_efficiency))
    fig.add_trace(go.Scatter(
        x=[0, max_eff],
        y=[0, 1],
        mode='lines',
        line=dict(color=COLORS['text_secondary'], dash='dash', width=1),
        showlegend=False,
        hoverinfo='skip',
    ))
    
    fig.update_layout(
        title=dict(
            text='Quality vs Efficiency Trade-off<br><sub>Top-right is optimal (high quality, high efficiency)</sub>',
            font=dict(size=20, color=COLORS['text'])
        ),
        height=450,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['surface'],
        font=dict(color=COLORS['text']),
        xaxis=dict(
            title='Efficiency (Quality per 1K tokens)',
            gridcolor=COLORS['grid'],
            showgrid=True,
            zeroline=False,
        ),
        yaxis=dict(
            title='Net Quality (Fidelity × (1 - Drift))',
            gridcolor=COLORS['grid'],
            showgrid=True,
            zeroline=False,
            range=[0, 1],
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor='rgba(0,0,0,0)',
        ),
        margin=dict(t=100, b=60, l=80, r=40),
    )
    
    return fig


def create_cost_savings_gauge(data: Dict) -> go.Figure:
    """Create gauge chart showing cost savings.
    
    Args:
        data: Evaluation data.
        
    Returns:
        Plotly figure.
    """
    json_tokens = sum(h['tokens_sent'] for h in data['json_pipeline']['handoffs'])
    md_tokens = sum(h['tokens_sent'] for h in data['markdown_pipeline']['handoffs'])
    
    savings_pct = ((json_tokens - md_tokens) / json_tokens * 100) if json_tokens > 0 else 0
    
    # Cost calculation ($0.50 per 1M tokens)
    cost_per_million = 0.50
    json_cost = (json_tokens / 1_000_000) * cost_per_million
    md_cost = (md_tokens / 1_000_000) * cost_per_million
    cost_savings = json_cost - md_cost
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=savings_pct,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={
            'text': f"Token Savings<br><sub>${cost_savings:.4f} saved per run</sub>",
            'font': {'size': 20, 'color': COLORS['text']}
        },
        delta={
            'reference': 50,
            'increasing': {'color': COLORS['success']},
            'suffix': '%'
        },
        number={
            'suffix': '%',
            'font': {'size': 48, 'color': COLORS['text']}
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
        height=300,
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['surface'],
        font=dict(color=COLORS['text']),
        margin=dict(t=80, b=20, l=20, r=20),
    )
    
    return fig


def create_recommendations_table(data: Dict) -> html.Div:
    """Create comparison table for final recommendations.
    
    Args:
        data: Evaluation data.
        
    Returns:
        Dash HTML div component.
    """
    json_recs = data['json_pipeline']['final_recommendations']
    md_recs = data['markdown_pipeline']['final_recommendations']
    
    # Create table rows
    rows = []
    for i in range(min(5, len(json_recs), len(md_recs))):
        json_rec = json_recs[i]
        md_rec = md_recs[i]
        
        match = json_rec['title'] == md_rec['title']
        
        rows.append(html.Tr([
            html.Td(str(i + 1), style={'textAlign': 'center', 'fontWeight': 'bold'}),
            html.Td([
                html.Div(json_rec['title'], style={'fontWeight': '500'}),
                html.Div(f"({json_rec['year']})", style={
                    'fontSize': '0.875rem',
                    'color': COLORS['text_secondary']
                })
            ]),
            html.Td([
                html.Div(md_rec['title'], style={'fontWeight': '500'}),
                html.Div(f"({md_rec['year']})", style={
                    'fontSize': '0.875rem',
                    'color': COLORS['text_secondary']
                })
            ]),
            html.Td(
                '✓' if match else '✗',
                style={
                    'textAlign': 'center',
                    'fontSize': '1.5rem',
                    'color': COLORS['success'] if match else COLORS['danger']
                }
            )
        ], style={
            'borderBottom': f'1px solid {COLORS["grid"]}',
        }))
    
    return html.Div([
        html.Table([
            html.Thead(html.Tr([
                html.Th('Rank', style={'textAlign': 'center'}),
                html.Th('JSON Pipeline'),
                html.Th('Markdown Pipeline'),
                html.Th('Match', style={'textAlign': 'center'}),
            ], style={
                'borderBottom': f'2px solid {COLORS["primary"]}',
                'color': COLORS['text'],
                'textTransform': 'uppercase',
                'fontSize': '0.875rem',
                'letterSpacing': '0.05em',
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


def create_dashboard(data: Dict) -> dash.Dash:
    """Create the main dashboard application.
    
    Args:
        data: Evaluation data.
        
    Returns:
        Dash application instance.
    """
    app = dash.Dash(__name__, title="ContextScope Evaluation Dashboard")
    
    # Calculate summary metrics
    json_summary = data['json_pipeline']['summary']
    md_summary = data['markdown_pipeline']['summary']
    comparison = data['comparison']
    
    json_tokens = sum(h['tokens_sent'] for h in data['json_pipeline']['handoffs'])
    md_tokens = sum(h['tokens_sent'] for h in data['markdown_pipeline']['handoffs'])
    token_savings_pct = ((json_tokens - md_tokens) / json_tokens * 100) if json_tokens > 0 else 0
    
    json_titles = {r['title'] for r in data['json_pipeline']['final_recommendations']}
    md_titles = {r['title'] for r in data['markdown_pipeline']['final_recommendations']}
    overlap = len(json_titles & md_titles)
    
    app.layout = html.Div([
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
                    f'Comparing JSON vs Markdown Context Formats • Evaluated: {data.get("evaluation_timestamp", "N/A")}',
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
            ], style={'flex': '1', 'minWidth': '250px'}),
            
            html.Div([
                create_metric_card(
                    'Markdown Quality',
                    f"{md_summary['end_to_end_quality']:.1%}",
                    f"Fidelity: {md_summary['avg_fidelity']:.2f} • Drift: {md_summary['avg_drift']:.2f}",
                    COLORS['markdown'],
                    '📝'
                )
            ], style={'flex': '1', 'minWidth': '250px'}),
            
            html.Div([
                create_metric_card(
                    'Token Savings',
                    f"{token_savings_pct:.0f}%",
                    f"{json_tokens - md_tokens:,} tokens saved",
                    COLORS['success'],
                    '💰'
                )
            ], style={'flex': '1', 'minWidth': '250px'}),
            
            html.Div([
                create_metric_card(
                    'Recommendation Match',
                    f"{overlap}/5",
                    f"{(overlap/5)*100:.0f}% overlap",
                    COLORS['warning'],
                    '🎯'
                )
            ], style={'flex': '1', 'minWidth': '250px'}),
        ], style={
            'display': 'flex',
            'gap': '1.5rem',
            'marginBottom': '2rem',
            'flexWrap': 'wrap',
        }),
        
        # Charts Row 1: Fidelity & Drift
        html.Div([
            html.Div([
                dcc.Graph(
                    figure=create_fidelity_drift_chart(data),
                    config={'displayModeBar': False},
                    style={'height': '100%'}
                )
            ], style={
                'background': COLORS['surface'],
                'borderRadius': '1rem',
                'padding': '1.5rem',
                'boxShadow': '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
                'border': f'1px solid {COLORS["grid"]}',
            })
        ], style={'marginBottom': '2rem'}),
        
        # Charts Row 2: Token Efficiency & Cost Savings
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
        
        # Charts Row 3: Quality vs Efficiency
        html.Div([
            html.Div([
                dcc.Graph(
                    figure=create_quality_efficiency_scatter(data),
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
        
        # Recommendations Comparison
        html.Div([
            html.H2('🎬 Final Recommendations Comparison', style={
                'margin': '0 0 1.5rem 0',
                'fontSize': '1.5rem',
                'fontWeight': '700',
                'color': COLORS['text']
            }),
            create_recommendations_table(data)
        ], style={'marginBottom': '2rem'}),
        
        # Footer
        html.Div([
            html.P([
                '💡 ',
                html.Strong('Key Insight: '),
                f"Markdown format achieves {100 - abs(comparison.get('quality_improvement', 0)) * 100:.0f}% similar quality ",
                f"with {token_savings_pct:.0f}% fewer tokens, resulting in significant cost savings and faster processing."
            ], style={
                'margin': '0',
                'fontSize': '1rem',
                'color': COLORS['text'],
                'textAlign': 'center'
            })
        ], style={
            'background': f'linear-gradient(135deg, {COLORS["primary"]}22 0%, {COLORS["secondary"]}22 100%)',
            'padding': '1.5rem',
            'borderRadius': '1rem',
            'border': f'1px solid {COLORS["grid"]}',
        })
        
    ], style={
        'maxWidth': '1400px',
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
                    transform: translateY(-2px);
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5) !important;
                }
                
                /* Scrollbar styling */
                ::-webkit-scrollbar {
                    width: 10px;
                    height: 10px;
                }
                
                ::-webkit-scrollbar-track {
                    background: ''' + COLORS['background'] + ''';
                }
                
                ::-webkit-scrollbar-thumb {
                    background: ''' + COLORS['grid'] + ''';
                    border-radius: 5px;
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
    
    return app 
def main():
    """Main entry point."""
    # Get evaluation file path
    if len(sys.argv) > 1:
        eval_file = sys.argv[1]
    else:
        eval_file = "reports/context_evaluation.json"
    
    # Check if file exists
    if not Path(eval_file).exists():
        print(f"Error: Evaluation file not found: {eval_file}")
        print("Please run demo_context_evaluation.py first to generate evaluation data.")
        sys.exit(1)
    
    # Load data
    print(f"Loading evaluation data from: {eval_file}")
    data = load_evaluation_data(eval_file)
    
    # Create and run dashboard
    print("Creating dashboard...")
    app = create_dashboard(data)
    
    print("\n" + "="*70)
    print("🚀 ContextScope Dashboard Running!")
    print("="*70)
    print("\n📊 Open your browser and navigate to: http://127.0.0.1:8050")
    print("\n💡 Press Ctrl+C to stop the server\n")
    
    # Use app.run instead of app.run_server
    app.run(debug=True, host='127.0.0.1', port=8050)

if __name__ == '__main__':
    main()