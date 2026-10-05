import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useTheme } from "@/app/ThemeProvider";
import type { TrafficPoint } from "@/features/dashboard/dashboardApi";
import { chartColors } from "@/lib/chartPalette";
import { formatBytes } from "@/lib/format";

export function TrafficChart({ data }: { data: TrafficPoint[] }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const colors = chartColors(theme);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={colors.gridline} vertical={false} />
        <XAxis
          dataKey="date"
          stroke={colors.axis}
          tick={{ fill: colors.mutedText, fontSize: 12 }}
          tickLine={false}
        />
        <YAxis
          stroke={colors.axis}
          tick={{ fill: colors.mutedText, fontSize: 12 }}
          tickLine={false}
          tickFormatter={(value: number) => formatBytes(value)}
          width={72}
        />
        <Tooltip
          formatter={(value: number, name: string) => [formatBytes(value), name]}
          contentStyle={{ fontSize: 12, background: colors.surface, color: colors.primaryText }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: colors.primaryText }} />
        <Line
          type="monotone"
          dataKey="download_bytes"
          name={t("dashboard.traffic.download")}
          stroke={colors.seriesDownload}
          strokeWidth={2}
          dot={{ r: 3 }}
        />
        <Line
          type="monotone"
          dataKey="upload_bytes"
          name={t("dashboard.traffic.upload")}
          stroke={colors.seriesUpload}
          strokeWidth={2}
          dot={{ r: 3 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
