import React from 'react';
import { ResponsiveLine } from '@nivo/line';
import { Box, Typography, Paper } from '@mui/material';
import { ResourceMetrics, CloudMetricsProps } from '../../types/CloudMetrics';

const ResourceMetricsChart: React.FC<CloudMetricsProps> = ({
  data,
  title = 'Resource Metrics',
  height = 400,
}) => {
  const metricsData = data as ResourceMetrics;

  const prepareLineData = () => {
    return [{
      id: metricsData.resourceType,
      data: metricsData.metrics.map((metric) => ({
        x: new Date(metric.timestamp).toLocaleString(),
        y: metric.value,
      })),
    }];
  };

  return (
    <Paper elevation={3} sx={{ p: 3, height: height + 100 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      <Typography variant="subtitle2" color="textSecondary" gutterBottom>
        {`Resource: ${metricsData.resourceId}`}
      </Typography>
      <Box sx={{ height: height }}>
        <ResponsiveLine
          data={prepareLineData()}
          margin={{ top: 50, right: 110, bottom: 50, left: 60 }}
          xScale={{
            type: 'time',
            format: '%Y-%m-%d %H:%M:%S',
            useUTC: false,
            precision: 'minute',
          }}
          xFormat="time:%Y-%m-%d %H:%M:%S"
          yScale={{
            type: 'linear',
            min: 'auto',
            max: 'auto',
          }}
          axisTop={null}
          axisRight={null}
          axisBottom={{
            format: '%H:%M',
            tickSize: 5,
            tickPadding: 5,
            tickRotation: -45,
            legend: 'Time',
            legendOffset: 36,
            legendPosition: 'middle',
          }}
          axisLeft={{
            tickSize: 5,
            tickPadding: 5,
            tickRotation: 0,
            legend: metricsData.metrics[0]?.unit || 'Value',
            legendOffset: -40,
            legendPosition: 'middle',
          }}
          enablePoints={true}
          pointSize={8}
          pointColor={{ theme: 'background' }}
          pointBorderWidth={2}
          pointBorderColor={{ from: 'serieColor' }}
          enableArea={true}
          areaOpacity={0.15}
          useMesh={true}
          enableSlices="x"
          legends={[
            {
              anchor: 'bottom-right',
              direction: 'column',
              justify: false,
              translateX: 100,
              translateY: 0,
              itemsSpacing: 0,
              itemDirection: 'left-to-right',
              itemWidth: 80,
              itemHeight: 20,
              symbolSize: 12,
              symbolShape: 'circle',
            },
          ]}
        />
      </Box>
    </Paper>
  );
};

export default ResourceMetricsChart;
