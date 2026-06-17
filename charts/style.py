def apply_chart_style(
    fig,
    title: str = "",
    is_pct: bool = True,
    theme_bg: str = "#F0F4F8",
    interactive: bool = False,
):
    kw = {"yaxis_tickformat": ".1%"} if is_pct else {}
    fig.update_layout(
        title=dict(text=title, font=dict(size=26)),
        plot_bgcolor=theme_bg,
        paper_bgcolor=theme_bg,
        hovermode="x unified",
        dragmode="zoom" if interactive else False,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=18),
        ),
        margin=dict(l=5, r=5, t=50, b=50),
        font=dict(size=18),
        **kw,
    )
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(0,0,0,0.05)",
        tickfont=dict(size=16),
        fixedrange=not interactive,
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="rgba(0,0,0,0.05)",
        tickfont=dict(size=16),
        fixedrange=not interactive,
    )
    return fig
