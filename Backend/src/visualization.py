import plotly.express as px
from . import data_processing
import pandas as pd

def plot_time_series_line_chart(youtube_df):

    # Convert "watch_date" column to datetime format with multiple potential formats
    youtube_df['watch_date'] = youtube_df['watch_date'].apply(data_processing.parse_timestamp)


    # Group by watch date and count the number of videos watched on each date
    df_grouped = youtube_df.groupby(youtube_df['watch_date'].dt.date).size().reset_index(name="count")

    # Calculate cumulative sum of the count
    df_grouped['cumulative_count'] = df_grouped['count'].cumsum()


    # Plot the time series line chart
    fig = px.line(df_grouped, x="watch_date", y="cumulative_count")

        # Adjust the layout to make the figure smaller
    fig.update_layout(
        width=600,  # Set the width of the figure (in pixels)
        height=300,  # Set the height of the figure (in pixels)
        xaxis_title="",  # Set the title for the x-axis
        yaxis_title="",  # Set the title for the y-axis
        margin=dict(l=10, r=20, t=20, b=10)  # Adjust margins (left, right, top, bottom) around the plot area

    )

    return fig

def plot_top_videos_chart(youtube_df):
    # Group by title and count the number of times each title appears
    df_grouped = youtube_df.groupby("title").size().reset_index(name="count")

    # Sort the DataFrame by count in descending order to plot the top videos
    df_grouped = df_grouped.sort_values(by="count", ascending=False)

    # Take only the top 10 titles
    df_top_10 = df_grouped.head(10)

    # Calculate cumulative sum of the count for each title
    df_top_10['cumulative_count'] = df_top_10['count'].cumsum()

    # Plot the bar chart
    fig = px.bar(df_top_10, x="title", y="cumulative_count")

        # Hide the x-axis labels
    fig.update_layout(
        xaxis = dict(
            tickmode = 'array',
            tickvals = []
        ),
    )

    # Adjust the layout to make the figure smaller
    fig.update_layout(
        width=400,  # Set the width of the figure (in pixels)
        height=200,  # Set the height of the figure (in pixels)
        xaxis_title="",  # Set the title for the x-axis
        yaxis_title="",  # Set the title for the y-axis
        margin=dict(l=5, r=10, t=10, b=10)  # Adjust margins (left, right, top, bottom) around the plot area

    )

    return fig


def plot_top_channels_chart(youtube_df):
    # Group by title and count the number of times each title appears
    df_grouped = youtube_df.groupby("channelTitle").size().reset_index(name="count")

    # Sort the DataFrame by count in descending order to plot the top videos
    df_grouped = df_grouped.sort_values(by="count", ascending=False)

    # Take only the top 10 titles
    df_top_10 = df_grouped.head(10)

    # Calculate cumulative sum of the count for each title
    df_top_10['cumulative_count'] = df_top_10['count'].cumsum()

    # Plot the bar chart
    fig = px.bar(df_top_10, x="channelTitle", y="cumulative_count")

    # Hide the x-axis labels
    fig.update_layout(
        xaxis = dict(
            tickmode = 'array',
            tickvals = []
        )
    )

    # Adjust the layout to make the figure smaller
    fig.update_layout(
        width=400,  # Set the width of the figure (in pixels)
        height=150,  # Set the height of the figure (in pixels)
        xaxis_title="",  # Set the title for the x-axis
        yaxis_title="",  # Set the title for the y-axis
        margin=dict(l=5, r=10, t=10, b=10)  # Adjust margins (left, right, top, bottom) around the plot area

    )

    return fig

def plot_heatmap(youtube_df,  date_column="watch_date"):

    # Create a DataFrame with day of the week and hour of the day
    df = pd.DataFrame(youtube_df[date_column], columns=[date_column])
    df["DayOfWeek"] = df[date_column].dt.dayofweek
    df["HourOfDay"] = df[date_column].dt.hour

    # Group data by day of the week and hour of the day
    heatmap_data = df.groupby(["DayOfWeek", "HourOfDay"]).size().unstack(fill_value=0)


    fig = px.imshow(heatmap_data, text_auto=True)

        # Hide the x-axis labels
    fig.update_layout(
        xaxis = dict(
            tickmode = 'array',
            ticktext = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        )
    )

    # Adjust the layout to make the figure smaller
    fig.update_layout(
        width=400,  # Set the width of the figure (in pixels)
        height=150,  # Set the height of the figure (in pixels)
        xaxis_title="Hour of Day",  # Set the title for the x-axis
        yaxis_title="Day of Week",  # Set the title for the y-axis
        margin=dict(l=10, r=10, t=20, b=10),  # Adjust margins (left, right, top, bottom) around the plot area
        coloraxis_colorbar=dict(title="Video Count")
    )


    return fig
