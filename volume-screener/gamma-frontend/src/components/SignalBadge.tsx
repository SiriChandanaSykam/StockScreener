import React from 'react';
import { SignalType } from '../types';

interface SignalBadgeProps {
    type: SignalType;
    className?: string;
}

const SignalBadge: React.FC<SignalBadgeProps> = ({ type, className = '' }) => {
    let styles = "bg-gray-700 text-gray-300";

    switch (type) {
        case SignalType.BUY:
            styles = "bg-green-900/30 text-green-400 border border-green-800/50";
            break;
        case SignalType.SELL:
            styles = "bg-red-900/30 text-red-400 border border-red-800/50";
            break;
        case SignalType.NEUTRAL:
            styles = "bg-gray-700/50 text-gray-400 border border-gray-600/50";
            break;
    }

    return (
        <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${styles} ${className}`}>
            {type}
        </span>
    );
};

export default SignalBadge;
