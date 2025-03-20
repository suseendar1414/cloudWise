import axios from 'axios';
import { CostData, ResourceMetrics } from '../types/CloudMetrics';

const api = axios.create({
  baseURL: '/api',
});

export const fetchCostAnalysis = async (provider: 'azure' | 'aws', timeframe: string): Promise<CostData> => {
  const response = await api.get(`/costs/${provider}`, {
    params: { timeframe },
  });
  return response.data;
};

export const fetchResourceMetrics = async (
  provider: 'azure' | 'aws',
  resourceId: string,
  metricName: string,
  timeframe: string
): Promise<ResourceMetrics> => {
  const response = await api.get(`/metrics/${provider}/${resourceId}`, {
    params: { metricName, timeframe },
  });
  return response.data;
};

export const listResources = async (provider: 'azure' | 'aws', resourceType: string) => {
  const response = await api.get(`/resources/${provider}`, {
    params: { type: resourceType },
  });
  return response.data;
};
