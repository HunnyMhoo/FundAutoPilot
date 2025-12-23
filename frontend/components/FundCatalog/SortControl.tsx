import { SortOption } from '@/utils/api/funds';

interface SortControlProps {
    value: SortOption;
    onChange: (value: SortOption) => void;
}

export function SortControl({ value, onChange }: SortControlProps) {
    return (
        <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">Sort by:</span>
            <select
                value={value}
                onChange={(e) => onChange(e.target.value as SortOption)}
                className="text-sm border-gray-200 rounded-lg focus:border-brand-primary focus:ring-brand-primary/20 py-1.5 pl-3 pr-8"
            >
                <option value="name_asc">Name (A-Z)</option>
                <option value="name_desc">Name (Z-A)</option>
                <option value="fee_asc">Fee (Low to High)</option>
                <option value="fee_desc">Fee (High to Low)</option>
                <option value="risk_asc">Risk (Low to High)</option>
                <option value="risk_desc">Risk (High to Low)</option>
            </select>
        </div>
    );
}
