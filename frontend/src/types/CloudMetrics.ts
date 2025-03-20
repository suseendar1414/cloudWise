export interface CostData {
  timeframe: string;
  startDate: string;
  endDate: string;
  currency: string;
  totalCost: number;
  costsByService: Record<string, number>;
  costsByLocation: Record<string, number>;
}

export interface ResourceMetrics {
  resourceId: string;
  resourceType: string;
  metrics: {
    timestamp: string;
    value: number;
    unit: string;
  }[];
}

export interface CloudMetricsProps {
  data: CostData | ResourceMetrics;
  type: 'cost' | 'resource';
  chartType?: 'line' | 'bar' | 'pie';
  title?: string;
  height?: number;
}
