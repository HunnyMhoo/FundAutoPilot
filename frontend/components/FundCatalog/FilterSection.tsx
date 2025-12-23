import styles from '../FundCatalog.module.css';

interface FilterSectionProps {
    title: string;
    items: { label: string; value: string; count?: number }[];
    selectedValues: string[];
    onToggle: (value: string) => void;
}

export function FilterSection({ title, items, selectedValues, onToggle }: FilterSectionProps) {
    return (
        <div className="mb-6">
            {title && (
                <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">
                    {title}
                </h3>
            )}
            <div className="space-y-2">
                {items.map((item) => {
                    const isSelected = selectedValues.includes(item.value);
                    return (
                        <label
                            key={item.value}
                            className="flex items-center group cursor-pointer"
                        >
                            <div className="relative flex items-center">
                                <input
                                    type="checkbox"
                                    className="peer h-4 w-4 rounded border-gray-300 text-brand-primary focus:ring-brand-primary/20 cursor-pointer"
                                    checked={isSelected}
                                    onChange={() => onToggle(item.value)}
                                />
                            </div>
                            <span className={`ml-2 text-sm ${isSelected ? 'text-gray-900 font-medium' : 'text-gray-600 group-hover:text-gray-900'}`}>
                                {item.label}
                            </span>
                        </label>
                    );
                })}
            </div>
        </div>
    );
}
