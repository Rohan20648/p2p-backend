# VoltShare P2P Energy — Backend API

Flask + PyMySQL backend for the VoltShare P2P electricity trading platform.

## Setup

```bash
cd p2p-backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Edit `.env` with your MySQL credentials:
```
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DB=p2p_energy
MYSQL_PORT=3306
PORT=3000
```

Run your MySQL schema SQL first, then:
```bash
python app.py
```
Server starts at `http://localhost:3000`

---

## API Endpoints

### Health
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/health | Server status |

### Users / Auth
| Method | URL | Description |
|--------|-----|-------------|
| POST | /api/users/register | Register new user |
| POST | /api/users/login | Login |
| GET | /api/users/ | All users (admin) |
| GET | /api/users/:id | Get user profile |
| PUT | /api/users/:id | Update user |

**Register body:** `{ full_name, email, password, role_id, phone? }`
**Login body:** `{ email, password }`

### Energy Listings (Marketplace)
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/listings/ | All listings (filter: ?status=active&zone_id=&slot_id=&source=) |
| GET | /api/listings/:id | Single listing |
| GET | /api/listings/seller/:seller_id | Seller's listings |
| POST | /api/listings/ | Create listing |
| PUT | /api/listings/:id/cancel | Cancel listing |
| DELETE | /api/listings/:id | Delete listing |

**Create body:** `{ seller_id, zone_id, slot_id, units_available_kwh, price_per_kwh, listing_date, energy_source_id?, expires_at? }`

### Orders & Trading
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/orders/ | All orders (?buyer_id=&status=) |
| GET | /api/orders/:id | Single order with match info |
| POST | /api/orders/ | Place order → auto-matches + processes payment |
| PUT | /api/orders/:id/cancel | Cancel order |

**Place order body:** `{ buyer_id, listing_id, units_requested_kwh }`  
⚡ This endpoint handles the full flow: match → transaction → wallet debit/credit.

### Transactions
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/transactions/ | All transactions (?user_id= or ?buyer_id=&seller_id=&status=) |
| GET | /api/transactions/:id | Single transaction |

### Wallet
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/wallet/:user_id | Get balance |
| POST | /api/wallet/:user_id/recharge | Recharge wallet |
| GET | /api/wallet/:user_id/recharge-history | Recharge logs |

**Recharge body:** `{ amount, payment_method, gateway_reference? }`

### Smart Meters & Energy Logs
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/meters/ | All meters (?user_id=) |
| GET | /api/meters/:id | Single meter |
| POST | /api/meters/ | Register meter |
| GET | /api/meters/:id/production | Production logs (?limit=50) |
| POST | /api/meters/:id/production | Log production |
| GET | /api/meters/:id/consumption | Consumption logs (?limit=50) |
| POST | /api/meters/:id/consumption | Log consumption |

### Zones / Lookup Data
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/zones/ | All grid zones |
| GET | /api/zones/:id | Single zone |
| GET | /api/zones/regions | All regions |
| GET | /api/zones/slots | All time slots |
| GET | /api/zones/sources | Renewable source types |
| GET | /api/zones/roles | User roles |

### Stats / Dashboard
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/stats/user/:user_id | User dashboard summary |
| GET | /api/stats/platform | Platform-wide stats (admin) |
| GET | /api/stats/zone/:zone_id | Zone-level stats |

### Notifications
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/notifications/:user_id | Get notifications (?unread=true) |
| PUT | /api/notifications/:id/read | Mark one read |
| PUT | /api/notifications/read-all/:user_id | Mark all read |
| POST | /api/notifications/ | Send notification |

### Disputes
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/disputes/ | All disputes (?status=open&user_id=) |
| GET | /api/disputes/:id | Single dispute |
| POST | /api/disputes/ | Raise dispute |
| PUT | /api/disputes/:id/resolve | Resolve dispute (admin) |

### Ratings
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/ratings/user/:user_id | Ratings received by user |
| POST | /api/ratings/ | Submit rating |

### Energy Sources (Installations)
| Method | URL | Description |
|--------|-----|-------------|
| GET | /api/energy-sources/ | All sources (?user_id=) |
| POST | /api/energy-sources/ | Add energy source |
| DELETE | /api/energy-sources/:id | Deactivate source |

---

## Frontend Integration

Update `script.js` line 10:
```js
const API = "http://localhost:3000";
```

Key flows:
- **Login** → `POST /api/users/login` → store `user_id` + `wallet_balance`
- **Load marketplace** → `GET /api/listings/?status=active`
- **Buy energy** → `POST /api/orders/` → deducts wallet automatically
- **Sell energy** → `POST /api/listings/`
- **Recharge wallet** → `POST /api/wallet/:uid/recharge`
- **View transactions** → `GET /api/transactions/?user_id=:uid`
- **Dashboard stats** → `GET /api/stats/user/:uid`
