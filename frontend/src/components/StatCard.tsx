interface StatCardProps {
  label: string;
  value: number;
  color: string;
}

export default function StatCard({ label, value, color }: StatCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex flex-col gap-1">
      <span className={`text-xs font-semibold uppercase tracking-wide ${color}`}>
        {label}
      </span>
      <span className="text-3xl font-bold text-gray-800">{value}</span>
    </div>
  );
}
