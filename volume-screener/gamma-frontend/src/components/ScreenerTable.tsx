import React, { useState, useMemo } from 'react';
import type { StockData } from '../types';
import { SignalType } from '../types';
import SignalBadge from './SignalBadge';

interface ScreenerTableProps {
    stocks: StockData[];
    onSelectStock: (stock: StockData) => void;
    selectedStockId?: string;
}

type SortKey = 'symbol' | 'price' | 'changePercent' | 'rvol' | 'rsi' | 'signal';
type SortOrder = 'asc' | 'desc';

const ScreenerTable: React.FC<ScreenerTableProps> = ({ stocks, onSelectStock, selectedStockId }) => {
    const [sortKey, setSortKey] = useState<SortKey>('changePercent');
    const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

    const handleSort = (key: SortKey) => {
        if (sortKey === key) {
            // Toggle order if same key
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            // New key, default to desc (high to low)
            setSortKey(key);
            setSortOrder('desc');
        }
    };

    const sortedStocks = useMemo(() => {
        const sorted = [...stocks].sort((a, b) => {
            let aVal: any, bVal: any;

            switch (sortKey) {
                case 'symbol':
                    aVal = a.symbol;
                    bVal = b.symbol;
                    break;
                case 'price':
                    aVal = a.price;
                    bVal = b.price;
                    break;
                case 'changePercent':
                    aVal = a.changePercent;
                    bVal = b.changePercent;
                    break;
                case 'rvol':
                    aVal = a.rvol;
                    bVal = b.rvol;
                    break;
                case 'rsi':
                    aVal = a.rsi;
                    bVal = b.rsi;
                    break;
                case 'signal':
                    // Sort by signal strength: BUY > NEUTRAL > SELL
                    const signalOrder = { BUY: 2, NEUTRAL: 1, SELL: 0 };
                    aVal = signalOrder[a.overallSignal as keyof typeof signalOrder] ?? 1;
                    bVal = signalOrder[b.overallSignal as keyof typeof signalOrder] ?? 1;
                    break;
                default:
                    return 0;
            }

            if (typeof aVal === 'string') {
                return sortOrder === 'asc'
                    ? aVal.localeCompare(bVal)
                    : bVal.localeCompare(aVal);
            }

            return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
        });

        return sorted;
    }, [stocks, sortKey, sortOrder]);

    const SortIcon = ({ columnKey }: { columnKey: SortKey }) => {
        if (sortKey !== columnKey) {
            return <span className="ml-1 text-gray-600">↕</span>;
        }
        return sortOrder === 'desc'
            ? <span className="ml-1 text-indigo-400">↓</span>
            : <span className="ml-1 text-indigo-400">↑</span>;
    };

    const SortableHeader = ({
        columnKey,
        label,
        className = ''
    }: {
        columnKey: SortKey;
        label: string;
        className?: string
    }) => (
        <th
            className={`p-4 font-medium cursor-pointer hover:text-indigo-400 transition-colors select-none ${className}`}
            onClick={() => handleSort(columnKey)}
        >
            <span className="flex items-center justify-inherit">
                {label}
                <SortIcon columnKey={columnKey} />
            </span>
        </th>
    );

    return (
        <div className="overflow-x-auto bg-gray-850 rounded-lg border border-gray-750">
            <table className="w-full text-left border-collapse">
                <thead>
                    <tr className="bg-gray-850 text-gray-400 text-xs uppercase tracking-wider border-b border-gray-750">
                        <SortableHeader columnKey="symbol" label="Symbol" />
                        <SortableHeader columnKey="price" label="Price" className="text-right" />
                        <SortableHeader columnKey="changePercent" label="Change" className="text-right" />
                        <SortableHeader columnKey="rvol" label="RVOL" className="text-center" />
                        <SortableHeader columnKey="rsi" label="RSI" className="text-center" />
                        <SortableHeader columnKey="signal" label="Signal" className="text-center" />
                        <th className="p-4 font-medium">Patterns</th>
                        <th className="p-4 font-medium min-w-[200px]">Strategies</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 text-sm">
                    {sortedStocks.map((stock) => {
                        const isSelected = selectedStockId === stock.symbol;
                        return (
                            <tr
                                key={stock.symbol}
                                onClick={() => onSelectStock(stock)}
                                className={`cursor-pointer transition-colors hover:bg-gray-800 ${isSelected ? 'bg-indigo-900/10 border-l-2 border-indigo-500' : ''}`}
                            >
                                <td className="p-4">
                                    <div className="font-bold text-gray-200">{stock.symbol}</div>
                                    <div className="text-xs text-gray-500">{stock.sector}</div>
                                </td>
                                <td className="p-4 text-right font-mono text-gray-300">
                                    {stock.price.toFixed(2)}
                                </td>
                                <td className={`p-4 text-right font-mono font-medium ${stock.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    {stock.changePercent > 0 ? '+' : ''}{stock.changePercent.toFixed(2)}%
                                </td>
                                <td className="p-4 text-center">
                                    <span className={`px-1.5 py-0.5 rounded text-xs ${stock.rvol > 2 ? 'bg-indigo-500/20 text-indigo-300' : 'text-gray-500'}`}>
                                        {stock.rvol.toFixed(1)}x
                                    </span>
                                </td>
                                <td className="p-4 text-center">
                                    <span className={`${stock.rsi > 70 || stock.rsi < 30 ? 'font-bold text-yellow-500' : 'text-gray-500'}`}>
                                        {stock.rsi.toFixed(0)}
                                    </span>
                                </td>
                                <td className="p-4 text-center">
                                    <SignalBadge type={stock.overallSignal} />
                                </td>
                                <td className="p-4">
                                    <div className="flex flex-wrap gap-1">
                                        {stock.activePatterns && stock.activePatterns.length > 0 ? (
                                            stock.activePatterns.map((p, i) => (
                                                <span key={i} className="px-2 py-0.5 rounded text-xs bg-orange-500/10 text-orange-300 border border-orange-500/20">
                                                    {p}
                                                </span>
                                            ))
                                        ) : (
                                            <span className="text-gray-600 text-xs">-</span>
                                        )}
                                    </div>
                                </td>
                                <td className="p-4">
                                    {stock.activeStrategies.length > 0 ? (
                                        <div className="flex flex-col gap-2">
                                            {stock.activeStrategies.slice(0, 2).map((s, idx) => {
                                                const isBuy = s.signal === SignalType.BUY;
                                                return (
                                                    <div key={idx} className={`flex flex-col border-l-2 pl-2 ${isBuy ? 'border-green-500/50' : 'border-red-500/50'}`}>
                                                        <span className={`text-xs font-bold ${isBuy ? 'text-green-400' : 'text-red-400'}`}>
                                                            {s.signal}
                                                        </span>
                                                        <span className="text-xs text-gray-300">{s.strategy}</span>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    ) : (
                                        <span className="text-xs text-gray-600">-</span>
                                    )}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
};

export default ScreenerTable;
