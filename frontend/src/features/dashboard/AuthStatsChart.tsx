import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useTheme } from "@/app/ThemeProvider";
import type { AuthStatPoint } from "@/features/dashboard/dashboardApi";
import { chartColors } from "@/lib/chartPalette";

export function AuthStatsChart({ data }: { data: AuthStatPoint[] }) {
  const { t } = useTranslation();
  const { theme } = useTheme();
  const colors = chartColors(theme);

  const points = data.map((point) => ({
    ...point,
    label: new Date(point.hour).toLocaleTimeString([], { hour: "2-digit" }),
  }));

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={points} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid stroke={colors.gridline} vertical={false} />
        <XAxis
          dataKey="label"
          stroke={colors.axis}
          tick={{ fill: colors.mutedText, fontSize: 12 }}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          stroke={colors.axis}
          tick={{ fill: colors.mutedText, fontSize: 12 }}
          tickLine={false}
          allowDecimals={false}
          width={40}
        />
        <Tooltip
          contentStyle={{ fontSize: 12, background: colors.surface, color: colors.primaryText }}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: colors.primaryText }} />
        <Bar
          dataKey="accept"
          name={t("dashboard.auth.accept")}
          fill={colors.statusGood}
          stackId="a"
        />
        <Bar
          dataKey="reject"
          name={t("dashboard.auth.reject")}
          fill={colors.statusCritical}
          stackId="a"
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
