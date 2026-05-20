import React from 'react';
import type { OHLC } from '../types';

interface ChartWidgetProps {
    symbol: string;
    history: OHLC[];
}

const ChartWidget: React.FC<ChartWidgetProps> = ({ symbol, history }) => {
    if (!history || history.length === 0) {
        return (
            <div className="bg-gray-850 rounded-lg p-4 border border-gray-750">
                <p className="text-gray-500">No chart data available</p>
            </div>
        );
    }

    // Calculate chart dimensions
    const width = 600;
    const height = 300;
    const padding = { top: 20, right: 20, bottom: 30, left: 50 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Get price range
    const prices = history.flatMap(h => [h.high, h.low]);
    const minPrice = Math.min(...prices) * 0.998;
    const maxPrice = Math.max(...prices) * 1.002;
    const priceRange = maxPrice - minPrice;

    // Scale functions
    const scaleX = (index: number) => padding.left + (index / (history.length - 1)) * chartWidth;
    const scaleY = (price: number) => padding.top + ((maxPrice - price) / priceRange) * chartHeight;

    // Calculate VWAP line
    const vwapLine = history
        .filter(h => h.vwap)
        .map((h, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(h.vwap!)}`)
        .join(' ');

    // Calculate close price line
    const closeLine = history
        .map((h, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(i)} ${scaleY(h.close)}`)
        .join(' ');

    // Open price reference
    const openPrice = history[0]?.open || 0;
    const openY = scaleY(openPrice);

    // Current price
    const currentPrice = history[history.length - 1]?.close || 0;
    const isUp = currentPrice >= openPrice;

    return (
        <div className="bg-gray-850 rounded-lg p-4 border border-gray-750">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold text-gray-200">{symbol} - Intraday Chart</h3>
                <span className={`text-sm font-bold ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                    ₹{currentPrice.toFixed(2)}
                </span>
            </div>

            <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
                {/* Grid lines */}
                {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                    const y = padding.top + ratio * chartHeight;
                    const price = maxPrice - ratio * priceRange;
                    return (
                        <g key={i}>
                            <line
                                x1={padding.left}
                                y1={y}
                                x2={width - padding.right}
                                y2={y}
                                stroke="#374151"
                                strokeDasharray="2,2"
                            />
                            <text x={padding.left - 5} y={y + 4} fill="#9CA3AF" fontSize="10" textAnchor="end">
                                {price.toFixed(0)}
                            </text>
                        </g>
                    );
                })}

                {/* Open price reference line */}
                <line
                    x1={padding.left}
                    y1={openY}
                    x2={width - padding.right}
                    y2={openY}
                    stroke="#6366f1"
                    strokeDasharray="4,4"
                    strokeOpacity={0.5}
                />
                <text x={width - padding.right + 5} y={openY + 4} fill="#6366f1" fontSize="9">
                    Open
                </text>

                {/* VWAP line */}
                {vwapLine && (
                    <path
                        d={vwapLine}
                        fill="none"
                        stroke="#f59e0b"
                        strokeWidth={1.5}
                        strokeOpacity={0.7}
                    />
                )}

                {/* Price line */}
                <path
                    d={closeLine}
                    fill="none"
                    stroke={isUp ? '#22c55e' : '#ef4444'}
                    strokeWidth={2}
                />

                {/* Area fill */}
                <path
                    d={`${closeLine} L ${scaleX(history.length - 1)} ${height - padding.bottom} L ${padding.left} ${height - padding.bottom} Z`}
                    fill={isUp ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)'}
                />

                {/* Candlesticks (simplified) */}
                {history.slice(-20).map((candle, i) => {
                    const idx = history.length - 20 + i;
                    if (idx < 0) return null;

                    const x = scaleX(idx);
                    const candleWidth = chartWidth / history.length * 0.6;
                    const isBullish = candle.close >= candle.open;

                    return (
                        <g key={i}>
                            {/* Wick */}
                            <line
                                x1={x}
                                y1={scaleY(candle.high)}
                                x2={x}
                                y2={scaleY(candle.low)}
                                stroke={isBullish ? '#22c55e' : '#ef4444'}
                                strokeWidth={1}
                            />
                            {/* Body */}
                            <rect
                                x={x - candleWidth / 2}
                                y={scaleY(Math.max(candle.open, candle.close))}
                                width={candleWidth}
                                height={Math.max(1, Math.abs(scaleY(candle.open) - scaleY(candle.close)))}
                                fill={isBullish ? '#22c55e' : '#ef4444'}
                                rx={1}
                            />
                        </g>
                    );
                })}

                {/* Time labels */}
                {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                    const idx = Math.floor(ratio * (history.length - 1));
                    const x = scaleX(idx);
                    return (
                        <text key={i} x={x} y={height - 8} fill="#9CA3AF" fontSize="10" textAnchor="middle">
                            {history[idx]?.time || ''}
                        </text>
                    );
                })}
            </svg>

            {/* Legend */}
            <div className="flex gap-4 mt-2 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                    <span className="w-3 h-0.5 bg-yellow-500"></span> VWAP
                </span>
                <span className="flex items-center gap-1">
                    <span className={`w-3 h-0.5 ${isUp ? 'bg-green-500' : 'bg-red-500'}`}></span> Price
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-3 h-0.5 bg-indigo-500"></span> Open
                </span>
            </div>
        </div>
    );
};

export default ChartWidget;
