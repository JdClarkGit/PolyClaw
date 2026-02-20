/**
 * PolyClaw Skills - PolyEdge API Integration
 * Custom skills for Polymarket analytics and trading intelligence
 */

const POLYEDGE_API = process.env.POLYEDGE_API_URL || 'http://localhost:8080';

export const skills = {
  /**
   * Fetch trades for a wallet
   */
  fetchTrades: {
    name: 'fetch_trades',
    description: 'Fetch trading history for a Polymarket wallet address',
    parameters: {
      type: 'object',
      properties: {
        wallet: {
          type: 'string',
          description: 'The wallet address (0x...)'
        },
        limit: {
          type: 'number',
          description: 'Number of trades to fetch (default: 1000)',
          default: 1000
        },
        mode: {
          type: 'string',
          enum: ['recent', 'full'],
          description: 'Fetch mode - recent or full history',
          default: 'recent'
        }
      },
      required: ['wallet']
    },
    async execute({ wallet, limit = 1000, mode = 'recent' }) {
      const url = mode === 'full' 
        ? `${POLYEDGE_API}/api/trades/${wallet}?mode=full`
        : `${POLYEDGE_API}/api/trades/${wallet}?limit=${limit}`;
      
      const response = await fetch(url);
      return await response.json();
    }
  },

  /**
   * Analyze wallet trading patterns
   */
  analyzeWallet: {
    name: 'analyze_wallet',
    description: 'Analyze trading patterns and performance for a wallet',
    parameters: {
      type: 'object',
      properties: {
        wallet: {
          type: 'string',
          description: 'The wallet address to analyze'
        },
        limit: {
          type: 'number',
          description: 'Number of trades to analyze',
          default: 1000
        }
      },
      required: ['wallet']
    },
    async execute({ wallet, limit = 1000 }) {
      const url = `${POLYEDGE_API}/api/analyze/${wallet}?limit=${limit}`;
      const response = await fetch(url);
      return await response.json();
    }
  },

  /**
   * Compare multiple wallets
   */
  compareWallets: {
    name: 'compare_wallets',
    description: 'Compare trading performance across multiple wallets',
    parameters: {
      type: 'object',
      properties: {
        wallets: {
          type: 'array',
          items: { type: 'string' },
          description: 'Array of wallet addresses to compare'
        },
        limit: {
          type: 'number',
          description: 'Number of trades per wallet',
          default: 1000
        }
      },
      required: ['wallets']
    },
    async execute({ wallets, limit = 1000 }) {
      const url = `${POLYEDGE_API}/api/compare`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallets, limit, tier: 'scale' })
      });
      return await response.json();
    }
  },

  /**
   * AI-powered deep analysis
   */
  aiAnalysis: {
    name: 'ai_deep_analysis',
    description: 'Run AI-powered deep analysis on wallet trading behavior',
    parameters: {
      type: 'object',
      properties: {
        wallet: {
          type: 'string',
          description: 'Wallet address to analyze'
        },
        analysisType: {
          type: 'string',
          enum: ['strategy', 'risk', 'performance', 'custom'],
          description: 'Type of analysis to perform',
          default: 'strategy'
        },
        customPrompt: {
          type: 'string',
          description: 'Custom question for analysis (only with custom type)'
        }
      },
      required: ['wallet']
    },
    async execute({ wallet, analysisType = 'strategy', customPrompt }) {
      const url = `${POLYEDGE_API}/api/ai-analyze/${wallet}`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: 'anthropic',
          prompt_type: analysisType,
          custom_prompt: customPrompt,
          limit: 1000
        })
      });
      return await response.json();
    }
  },

  /**
   * Get Polymarket market data
   */
  getMarketData: {
    name: 'get_market_data',
    description: 'Fetch current market data from Polymarket',
    parameters: {
      type: 'object',
      properties: {
        marketSlug: {
          type: 'string',
          description: 'Market slug or ID'
        }
      },
      required: ['marketSlug']
    },
    async execute({ marketSlug }) {
      const url = `https://polymarket.com/api/markets/${marketSlug}`;
      const response = await fetch(url);
      return await response.json();
    }
  },

  /**
   * Calculate position size using Kelly criterion
   */
  calculateKelly: {
    name: 'calculate_kelly',
    description: 'Calculate optimal position size using Kelly criterion',
    parameters: {
      type: 'object',
      properties: {
        probability: {
          type: 'number',
          description: 'Your estimated probability of winning (0-1)'
        },
        odds: {
          type: 'number',
          description: 'The odds offered (e.g., 2.0 for even odds)'
        },
        bankroll: {
          type: 'number',
          description: 'Your total bankroll in USDC'
        },
        fractionKelly: {
          type: 'number',
          description: 'Fraction of Kelly to use (0.25-0.5 recommended)',
          default: 0.25
        }
      },
      required: ['probability', 'odds', 'bankroll']
    },
    execute({ probability, odds, bankroll, fractionKelly = 0.25 }) {
      const q = 1 - probability;
      const b = odds - 1;
      const kelly = (probability * b - q) / b;
      const adjustedKelly = Math.max(0, kelly * fractionKelly);
      const positionSize = bankroll * adjustedKelly;
      
      return {
        fullKelly: kelly,
        adjustedKelly,
        recommendedPosition: positionSize,
        maxLoss: positionSize,
        expectedValue: positionSize * (probability * odds - 1),
        recommendation: kelly <= 0 ? 'NO BET - Negative EV' : `Bet $${positionSize.toFixed(2)}`
      };
    }
  },

  /**
   * Detect arbitrage opportunities
   */
  findArbitrage: {
    name: 'find_arbitrage',
    description: 'Analyze related markets for arbitrage opportunities',
    parameters: {
      type: 'object',
      properties: {
        market1Price: {
          type: 'number',
          description: 'Price of YES in market 1 (0-1)'
        },
        market2Price: {
          type: 'number',
          description: 'Price of YES in market 2 (0-1)'  
        },
        correlation: {
          type: 'string',
          enum: ['same', 'opposite', 'partial'],
          description: 'Relationship between markets'
        }
      },
      required: ['market1Price', 'market2Price', 'correlation']
    },
    execute({ market1Price, market2Price, correlation }) {
      let arbOpportunity = false;
      let strategy = '';
      let profit = 0;

      if (correlation === 'same') {
        if (market1Price + (1 - market2Price) < 1) {
          arbOpportunity = true;
          profit = 1 - market1Price - (1 - market2Price);
          strategy = `Buy YES in Market 1 @ ${market1Price}, Buy NO in Market 2 @ ${1-market2Price}`;
        }
      } else if (correlation === 'opposite') {
        if (market1Price + market2Price < 1) {
          arbOpportunity = true;
          profit = 1 - market1Price - market2Price;
          strategy = `Buy YES in both markets`;
        }
      }

      return {
        hasArbitrage: arbOpportunity,
        profitPerDollar: profit,
        strategy: strategy || 'No arbitrage detected',
        recommendation: arbOpportunity ? `Guaranteed ${(profit * 100).toFixed(2)}% profit` : 'No risk-free profit available'
      };
    }
  }
};

export default skills;
