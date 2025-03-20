import React, { useState, useEffect } from 'react';
import { Grid, Container, Paper, Typography, Box, ToggleButton, ToggleButtonGroup } from '@mui/material';
import CostChart from './charts/CostChart';
import ResourceMetricsChart from './charts/ResourceMetricsChart';
import { CostData, ResourceMetrics } from '../types/CloudMetrics';
import { fetchCostAnalysis, fetchResourceMetrics } from '../services/api';

const Dashboard: React.FC = () => {
  const [provider, setProvider] = useState<'azure' | 'aws'>('azure');
  const [timeframe, setTimeframe] = useState<'LastWeek' | 'LastMonth'>('LastMonth');
  const [costData, setCostData] = useState<CostData | null>(null);
  const [resourceMetrics, setResourceMetrics] = useState<ResourceMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch cost data
        const costs = await fetchCostAnalysis(provider, timeframe);
        setCostData(costs);

        // Fetch CPU metrics for a sample resource
        const metrics = await fetchResourceMetrics(
          provider,
          provider === 'azure' ? 'sample-vm-id' : 'i-1234567890abcdef0',
          'CPUUtilization',
          timeframe
        );
        setResourceMetrics(metrics);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [provider, timeframe]);

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" gutterBottom>
          Cloud Resources Dashboard
        </Typography>

        <Box sx={{ mb: 4 }}>
          <ToggleButtonGroup
            value={provider}
            exclusive
            onChange={(_, newProvider) => newProvider && setProvider(newProvider)}
            aria-label="cloud provider"
          >
            <ToggleButton value="azure" aria-label="azure">
              Azure
            </ToggleButton>
            <ToggleButton value="aws" aria-label="aws">
              AWS
            </ToggleButton>
          </ToggleButtonGroup>

          <ToggleButtonGroup
            value={timeframe}
            exclusive
            onChange={(_, newTimeframe) => newTimeframe && setTimeframe(newTimeframe)}
            aria-label="timeframe"
            sx={{ ml: 2 }}
          >
            <ToggleButton value="LastWeek" aria-label="last week">
              Last Week
            </ToggleButton>
            <ToggleButton value="LastMonth" aria-label="last month">
              Last Month
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        {error ? (
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography color="error">{error}</Typography>
          </Paper>
        ) : loading ? (
          <Paper elevation={3} sx={{ p: 3, mb: 3 }}>
            <Typography>Loading...</Typography>
          </Paper>
        ) : (
          <Grid container spacing={3}>
            {costData && (
              <>
                <Grid item xs={12}>
                  <Typography variant="h5" gutterBottom>
                    Cost Analysis
                  </Typography>
                </Grid>

                <Grid item xs={12} md={6}>
                  <CostChart
                    data={costData}
                    type="cost"
                    chartType="bar"
                    title="Cost by Service"
                    height={300}
                  />
                </Grid>

                <Grid item xs={12} md={6}>
                  <CostChart
                    data={costData}
                    type="cost"
                    chartType="pie"
                    title="Cost Distribution"
                    height={300}
                  />
                </Grid>
              </>
            )}

            {resourceMetrics && (
              <>
                <Grid item xs={12}>
                  <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
                    Resource Metrics
                  </Typography>
                </Grid>

                <Grid item xs={12}>
                  <ResourceMetricsChart
                    data={resourceMetrics}
                    type="resource"
                    title="CPU Utilization Over Time"
                    height={300}
                  />
                </Grid>
              </>
            )}
          </Grid>
        )}
      </Box>
    </Container>
  );
};

export default Dashboard;
