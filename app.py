import matplotlib.pyplot as plt
import polars as pl
import streamlit as st
from matplotlib import style
from matplotlib.patches import Patch
from matplotlib.ticker import StrMethodFormatter

st.set_page_config(page_title='NYC Parking Tickets', layout='wide')


@st.cache_data  # read the CSV once, not on every widget change
def load_data():
    return pl.read_csv('socrata_data.csv', infer_schema_length=2000)


def top_fines(df, state, n=10):
    return (
        df.lazy()
        .filter(pl.col('state') == state)
        .group_by('issuing_agency', 'violation')
        .agg(pl.col('fine_amount').sum(),
             pl.col('violation').count().alias('count'))
        .sort('fine_amount', descending=True)
        .head(n)
        .collect()
    )


def plot_top_fines(data, state, n):
    data = data.sort('fine_amount')  # ascending, so the largest bar is on top

    agencies = sorted(data['issuing_agency'].unique().to_list())
    cb10 = style.library['tableau-colorblind10']['axes.prop_cycle'].by_key()['color']
    color = {a: cb10[i % len(cb10)] for i, a in enumerate(agencies)}

    fig, ax = plt.subplots(figsize=(10, 0.5 * data.height + 1.5))
    y = range(data.height)  # numeric positions keep repeated violations as separate bars
    bars = ax.barh(y, data['fine_amount'],
                   color=[color[a] for a in data['issuing_agency']])

    ax.set_yticks(y, data['violation'].to_list())
    ax.bar_label(bars, labels=[f'${v:,.0f}  ({c:,})' for v, c in
                               zip(data['fine_amount'], data['count'])],
                 padding=4, fontsize=9)
    ax.xaxis.set_major_formatter(StrMethodFormatter('${x:,.0f}'))
    ax.margins(x=0.2)  # leave room for the bar labels
    ax.spines[['top', 'right']].set_visible(False)

    ax.legend(handles=[Patch(color=color[a], label=a) for a in agencies],
              title='Issuing agency', loc='lower right', frameon=True)
    ax.set_title(f'Top {n} violations by total fine amount — {state}')
    ax.set_xlabel('Total fine amount')
    fig.tight_layout()
    return fig


df = load_data()

st.title('2025 NYC Parking Tickets')

states = sorted(df['state'].drop_nulls().unique().to_list())
with st.sidebar:
    state = st.selectbox('Plate state', states,
                         index=states.index('NY') if 'NY' in states else 0)
    n = st.slider('Number of violations', 5, 25, 10)

data = top_fines(df, state, n)
if data.is_empty():
    st.info(f'No tickets found for {state}.')
else:
    st.pyplot(plot_top_fines(data, state, n))
    with st.expander('Show data'):
        st.dataframe(data)
