import React from 'react';
import { ResponsiveLine } from '@nivo/line';
import { ResponsiveBar } from '@nivo/bar';
import { ResponsivePie } from '@nivo/pie';
import { Box, Typography, Paper } from '@mui/material';
import { CostData, CloudMetricsProps } from '../../types/CloudMetrics';

const formatCurrency = (value: number, currency: string) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency || 'USD',
  }).format(value);
};

const CostChart: React.FC<CloudMetricsProps> = ({
  data,
  chartType = 'bar',
  title = 'Cost Analysis',
  height = 400,
}) => {
  const costData = data as CostData;
  
  const prepareLineData = () => {
    const serviceData = Object.entries(costData.costsByService).map(([service, cost]) => ({
      x: service,
      y: cost,
    }));

    return [{
      id: 'Service Costs',
      data: serviceData,
    }];
  };

  const prepareBarData = () => {
    return Object.entries(costData.costsByService).map(([service, cost]) => ({
      service,
      cost,
    }));
  };

  const preparePieData = () => {
    return Object.entries(costData.costsByService).map(([service, cost]) => ({
      id: service,
      label: service,
      value: cost,
    }));
  };

  const renderChart = () => {
    switch (chartType) {
      case 'line':
        return (
          <ResponsiveLine
            data={prepareLineData()}
            margin={{ top: 50, right: 110, bottom: 50, left: 60 }}
            xScale={{ type: 'point' }}
            yScale={{ type: 'linear', min: 0, max: 'auto' }}
            axisTop={null}
            axisRight={null}
            axisBottom={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: -45,
            }}
            axisLeft={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: 0,
              format: (value) => formatCurrency(value, costData.currency),
            }}
            pointSize={10}
            pointColor={{ theme: 'background' }}
            pointBorderWidth={2}
            pointBorderColor={{ from: 'serieColor' }}
            enablePointLabel={true}
            pointLabel="y"
            pointLabelYOffset={-12}
            enableArea={true}
            areaOpacity={0.15}
            useMesh={true}
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
        );

      case 'bar':
        return (
          <ResponsiveBar
            data={prepareBarData()}
            keys={['cost']}
            indexBy="service"
            margin={{ top: 50, right: 130, bottom: 50, left: 60 }}
            padding={0.3}
            valueScale={{ type: 'linear' }}
            indexScale={{ type: 'band', round: true }}
            colors={{ scheme: 'nivo' }}
            borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
            axisTop={null}
            axisRight={null}
            axisBottom={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: -45,
            }}
            axisLeft={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: 0,
              format: (value) => formatCurrency(value, costData.currency),
            }}
            labelSkipWidth={12}
            labelSkipHeight={12}
            labelTextColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
            legends={[
              {
                dataFrom: 'keys',
                anchor: 'bottom-right',
                direction: 'column',
                justify: false,
                translateX: 120,
                translateY: 0,
                itemsSpacing: 2,
                itemWidth: 100,
                itemHeight: 20,
                itemDirection: 'left-to-right',
                itemOpacity: 0.85,
                symbolSize: 20,
              },
            ]}
          />
        );

      case 'pie':
        return (
          <ResponsivePie
            data={preparePieData()}
            margin={{ top: 40, right: 80, bottom: 80, left: 80 }}
            innerRadius={0.5}
            padAngle={0.7}
            cornerRadius={3}
            activeOuterRadiusOffset={8}
            borderWidth={1}
            borderColor={{ from: 'color', modifiers: [['darker', 0.2]] }}
            arcLinkLabelsSkipAngle={10}
            arcLinkLabelsTextColor="#333333"
            arcLinkLabelsThickness={2}
            arcLinkLabelsColor={{ from: 'color' }}
            arcLabelsSkipAngle={10}
            arcLabelsTextColor={{ from: 'color', modifiers: [['darker', 2]] }}
            legends={[
              {
                anchor: 'bottom',
                direction: 'row',
                justify: false,
                translateX: 0,
                translateY: 56,
                itemsSpacing: 0,
                itemWidth: 100,
                itemHeight: 18,
                itemTextColor: '#999',
                itemDirection: 'left-to-right',
                itemOpacity: 1,
                symbolSize: 18,
                symbolShape: 'circle',
              },
            ]}
          />
        );

      default:
        return null;
    }
  };

  return (
    <Paper elevation={3} sx={{ p: 3, height: height + 100 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      <Typography variant="subtitle2" color="textSecondary" gutterBottom>
        {`${costData.timeframe} (${costData.startDate} - ${costData.endDate})`}
      </Typography>
      <Typography variant="h5" gutterBottom>
        Total: {formatCurrency(costData.totalCost, costData.currency)}
      </Typography>
      <Box sx={{ height: height }}>
        {renderChart()}
      </Box>
    </Paper>
  );
};

export default CostChart;
