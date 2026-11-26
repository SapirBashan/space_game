import { Component, signal, effect, HostListener, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { trigger, state, style, animate, transition, keyframes, query, stagger } from '@angular/animations';

interface GameObject { id: number; x: number; y: number; width: number; height: number; active: boolean; type?: number; speedX?: number; speedY?: number; rewardType?: number; }
interface Explosion { id: number; x: number; y: number; particles: { x: number; y: number; vx: number; vy: number; life: number; color: string }[]; }
interface Star { x: number; y: number; speed: number; size: number; }

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  animations: [
    trigger('quantumCore', [
      state('idle', style({ transform: 'scale(1) rotateX(0deg) rotateY(0deg)', filter: 'hue-rotate(0deg) drop-shadow(0 0 20px rgba(0, 255, 255, 0.8))', opacity: 1 })),
      state('leaping', style({ transform: 'scale(0.01) rotateX(1080deg) rotateY(1080deg)', filter: 'hue-rotate(360deg) drop-shadow(0 0 100px rgba(255, 0, 255, 1))', opacity: 0 })),
      transition('idle => leaping', [
        animate('2.5s cubic-bezier(0.68, -0.55, 0.265, 1.55)', keyframes([
          style({ transform: 'scale(1.3) rotateX(45deg)', filter: 'hue-rotate(90deg) blur(2px)', offset: 0.2 }),
          style({ transform: 'scale(1.5) rotateY(90deg)', filter: 'hue-rotate(180deg) blur(5px)', offset: 0.4 }),
          style({ transform: 'scale(0.1) rotateX(720deg)', filter: 'hue-rotate(270deg) blur(20px)', offset: 0.8 }),
          style({ transform: 'scale(0)', filter: 'hue-rotate(360deg) blur(50px)', opacity: 0, offset: 1.0 })
        ]))
      ])
    ]),
    trigger('particleMatrix', [
      transition('* => *', [
        query(':enter', [
          style({ opacity: 0, transform: 'translate3d(0, -150px, -500px) scale(0)' }),
          stagger(30, [animate('0.6s cubic-bezier(0.2, 0.8, 0.2, 1)', style({ opacity: 1, transform: 'translate3d(0, 0, 0) scale(1)' }))])
        ], { optional: true }),
        query(':leave', [
          stagger(20, [animate('0.3s ease-out', style({ opacity: 0, transform: 'translate3d(0, 100px, 500px) scale(0)' }))])
        ], { optional: true })
      ])
    ]),
    trigger('hudFade', [
      transition(':enter', [style({ opacity: 0, transform: 'translateY(50px)' }), animate('1s 1s ease-out', style({ opacity: 1, transform: 'translateY(0)' }))]),
      transition(':leave', [animate('0.5s ease-in', style({ opacity: 0, transform: 'translateY(-50px)' }))])
    ])
  ],
  template: `
    <div class="quantum-container">

      <!-- DEFAULT MODE -->
      @if (!gameMode()) {
        <div class="hud" @hudFade>
          <h1>SYSTEM: <span class="accent">QUANTUM NEXUS</span></h1>
          <div class="status-bar">
            <div class="label">LEAP STATUS:</div>
            <div class="value" [class.active]="leapState() === 'leaping'">
              {{ leapState() === 'leaping' ? 'INITIATING TRAVERSAL...' : 'STABLE' }}
            </div>
          </div>
        </div>

        <div class="core-wrapper">
          <div class="quantum-core" [@quantumCore]="leapState()" (click)="initiateLeap()">
            <div class="ring ring-1"></div>
            <div class="ring ring-2"></div>
            <div class="ring ring-3"></div>
            <div class="core-text">INITIATE</div>
          </div>
        </div>

        <div class="particle-matrix" [@particleMatrix]="particles().length">
          @for (p of particles(); track p.id) {
            <div class="particle" [style.left.%]="p.x" [style.top.%]="p.y" [style.animationDelay.s]="p.delay" [style.backgroundColor]="p.color"></div>
          }
        </div>
      }

      <!-- STARSHIP GAME MODE -->
      @if (gameMode()) {
        <div class="game-hud">
          <div class="score">SCORE: {{ score() }} <span class="level">LVL {{ level() }}</span></div>
          <div class="instructions">ARROWS/WASD to Move | SPACE to Shoot | V to Toggle {{ is3D() ? '2D' : '3D' }} | ESC to Abort</div>
        </div>

        <div class="game-area-wrapper">
          <div class="game-area"
               [style.transform]="is3D() ? 'rotateY(' + cameraPan() + 'deg) rotateX(10deg)' : 'none'">

            <!-- Parallax Stars -->
            @for (star of stars(); track $index) {
              <div class="star"
                   [style.left.px]="star.x"
                   [style.bottom.px]="star.y"
                   [style.width.px]="star.size"
                   [style.height.px]="star.size"
                   [style.transform]="is3D() ? 'translateZ(' + (-star.size * 50) + 'px)' : 'none'"></div>
            }

            @if (isGameOver()) {
              <div class="game-over-screen" [style.transform]="is3D() ? 'translate(-50%, -50%) translateZ(100px)' : 'translate(-50%, -50%)'">
                <h2>SYSTEM FAILURE</h2>
                <div class="final-score">SCORE: {{ score() }}</div>
                <div class="retry-hint">Press [R] to Restart or [ESC] to Abort</div>
              </div>
            }

            <!-- Player Ship -->
            @if (!isGameOver()) {
              <div class="player-ship"
                   [class.boosted]="boostActive()"
                   [class.shielded]="shieldActive()"
                   [style.left.px]="playerX()"
                   [style.bottom.px]="60"
                   [style.transform]="'translateX(-50%) ' + (is3D() ? 'rotateY(' + shipTilt() + 'deg) rotateZ(' + (shipTilt() / 3) + 'deg) translateZ(50px)' : '')">
                <div class="hull">▲</div>
                <div class="wing left">/</div>
                <div class="wing right">\\</div>
                <div class="thruster"></div>
              </div>
            }

            <!-- Lasers -->
            @for (laser of lasers(); track laser.id) {
              @if (laser.active) {
                <div class="laser" [style.left.px]="laser.x" [style.bottom.px]="laser.y" [style.transform]="is3D() ? 'translateZ(50px) translateX(-50%)' : 'translateX(-50%)'">|</div>
              }
            }

            <!-- Enemies -->
            @for (enemy of enemies(); track enemy.id) {
              @if (enemy.active) {
                <div class="enemy"
                     [class.fast]="enemy.type === 1"
                     [style.left.px]="enemy.x"
                     [style.bottom.px]="enemy.y"
                     [style.transform]="is3D() ? 'translateZ(50px) translateX(-50%)' : 'translateX(-50%)'">
                  {{ enemy.type === 1 ? '☠' : '▼' }}
                </div>
              }
            }

            <!-- Rewards -->
            @for (reward of rewards(); track reward.id) {
              @if (reward.active) {
                <div class="reward"
                     [class.shield-reward]="reward.rewardType === 1"
                     [style.left.px]="reward.x"
                     [style.bottom.px]="reward.y"
                     [style.transform]="is3D() ? 'translateZ(50px) translateX(-50%)' : 'translateX(-50%)'">
                  {{ reward.rewardType === 1 ? '◎' : '★' }}
                </div>
              }
            }

            <!-- Explosions -->
            @for (exp of explosions(); track exp.id) {
              <div class="explosion-container" [style.left.px]="exp.x" [style.bottom.px]="exp.y" [style.transform]="is3D() ? 'translateZ(50px) translateX(-50%)' : 'translateX(-50%)'">
                @for (p of exp.particles; track $index) {
                  <div class="explosion-particle" [style.left.px]="p.x" [style.bottom.px]="p.y" [style.backgroundColor]="p.color" [style.opacity]="p.life"></div>
                }
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; width: 100vw; height: 100vh; }
    ::ng-deep body { margin: 0; padding: 0; overflow: hidden; background: #050510; }
    .quantum-container { position: relative; width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; overflow: hidden; background: transparent; }
    /* --- HUD & Core --- */
    .hud { position: absolute; top: 40px; left: 40px; z-index: 10; h1 { font-size: 2rem; margin: 0 0 10px 0; letter-spacing: 4px; text-shadow: 0 0 10px rgba(0, 255, 255, 0.5); } .accent { color: #0ff; } .status-bar { display: flex; gap: 15px; font-size: 1.2rem; } .label { color: #888; } .value { color: #0f0; text-shadow: 0 0 5px #0f0; transition: color 0.3s; } .value.active { color: #f0f; text-shadow: 0 0 10px #f0f; animation: pulseText 0.5s infinite alternate; } }
    .core-wrapper { position: relative; z-index: 5; perspective: 1000px; }
    .quantum-core { width: 250px; height: 250px; position: relative; display: flex; align-items: center; justify-content: center; cursor: pointer; transform-style: preserve-3d; .core-text { font-size: 1.5rem; font-weight: 900; letter-spacing: 5px; color: #fff; text-shadow: 0 0 15px #0ff; z-index: 10; pointer-events: none; } .ring { position: absolute; border-radius: 50%; border: 2px solid transparent; border-top-color: #0ff; border-bottom-color: #f0f; box-shadow: 0 0 20px rgba(0, 255, 255, 0.2), inset 0 0 20px rgba(255, 0, 255, 0.2); } .ring-1 { width: 100%; height: 100%; animation: spin 4s linear infinite; } .ring-2 { width: 80%; height: 80%; animation: spin 3s linear infinite reverse; border-left-color: #0ff; border-right-color: #f0f; } .ring-3 { width: 60%; height: 60%; animation: spin 2s linear infinite; border-top-color: #fff; border-bottom-color: #fff; } &:hover .ring { animation-duration: 1s; box-shadow: 0 0 40px rgba(0, 255, 255, 0.6), inset 0 0 40px rgba(255, 0, 255, 0.6); } }
    .particle-matrix { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1; .particle { position: absolute; width: 6px; height: 6px; border-radius: 50%; box-shadow: 0 0 10px currentColor; animation: float 4s ease-in-out infinite alternate; } }

    /* --- GAME STYLES --- */
    .game-hud { position: absolute; top: 20px; width: 100%; display: flex; justify-content: space-between; padding: 0 40px; z-index: 30; pointer-events: none; .score { font-size: 2rem; color: #0ff; text-shadow: 0 0 10px #0ff; font-weight: bold; .level { color: #f0f; font-size: 1.2rem; text-shadow: 0 0 10px #f0f; margin-left: 20px; } } .instructions { color: #888; font-size: 1rem; align-self: flex-end; } }

    .game-area-wrapper { position: absolute; top: 0; left: 0; width: 100%; height: 100%; perspective: 800px; overflow: hidden; }
    .game-area { position: absolute; bottom: 0; left: -10%; width: 120%; height: 120%; transform-style: preserve-3d; transition: transform 0.1s ease-out; background: radial-gradient(circle at center, rgba(20,0,50,0.5) 0%, transparent 80%); }

    .star { position: absolute; background: #fff; border-radius: 50%; box-shadow: 0 0 8px #fff; }

    .game-over-screen { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; z-index: 50; h2 { color: #f00; font-size: 4rem; letter-spacing: 10px; margin: 0 0 20px 0; text-shadow: 0 0 20px #f00, 0 0 40px #f00; animation: glitch 0.2s infinite; } .final-score { font-size: 2.5rem; color: #0ff; text-shadow: 0 0 10px #0ff; margin-bottom: 30px; } .retry-hint { color: #fff; font-size: 1.2rem; letter-spacing: 2px; animation: pulseText 1s infinite alternate; } }

    .player-ship {
      position: absolute; color: #0ff; text-shadow: 0 0 15px #0ff; font-weight: bold; display: flex; flex-direction: column; align-items: center; z-index: 20;
      transform-style: preserve-3d;
      .hull { font-size: 40px; line-height: 1; }
      .wing { position: absolute; top: 15px; font-size: 30px; color: #08f; transform: translateZ(-10px); }
      .wing.left { left: -15px; }
      .wing.right { right: -15px; }
      .thruster { position: absolute; bottom: -20px; left: 50%; transform: translateX(-50%) translateZ(-5px); width: 16px; height: 25px; background: #f0f; box-shadow: 0 0 20px #f0f, 0 0 40px #f0f; clip-path: polygon(50% 100%, 0 0, 100% 0); animation: thrust 0.05s infinite alternate; }
    }
    .player-ship.boosted .hull { color: #0f0; text-shadow: 0 0 20px #0f0, 0 0 40px #0f0; }
    .player-ship.shielded::after { content: ''; position: absolute; top: -15px; left: -35px; right: -35px; bottom: -15px; border-radius: 50%; border: 2px solid #08f; box-shadow: 0 0 20px #08f, inset 0 0 20px #08f; animation: pulseReward 0.5s infinite alternate; pointer-events: none; }

    .laser { position: absolute; font-size: 25px; color: #f0f; text-shadow: 0 0 15px #f0f, 0 0 30px #f0f; font-weight: bold; z-index: 15; }
    .enemy { position: absolute; font-size: 35px; color: #f00; text-shadow: 0 0 20px #f00; z-index: 15; transform-style: preserve-3d; }
    .enemy.fast { color: #ff3300; text-shadow: 0 0 20px #ff3300, 0 0 40px #ff0000; font-size: 45px; animation: spinEnemy 0.3s linear infinite; }

    .reward { position: absolute; font-size: 50px; color: #0f0; text-shadow: 0 0 20px #0f0, 0 0 40px #0f0; z-index: 15; transform-style: preserve-3d; animation: pulseReward 0.5s infinite alternate; }
    .reward.shield-reward { color: #08f; text-shadow: 0 0 20px #08f, 0 0 40px #08f; }

    .explosion-container { position: absolute; z-index: 10; transform-style: preserve-3d; }
    .explosion-particle { position: absolute; width: 6px; height: 6px; border-radius: 50%; box-shadow: 0 0 15px currentColor; }

    @keyframes spin { 0% { transform: rotateX(60deg) rotateY(0deg) rotateZ(0deg); } 100% { transform: rotateX(60deg) rotateY(360deg) rotateZ(360deg); } }
    @keyframes float { 0% { transform: translateY(0) scale(1); opacity: 0.5; } 100% { transform: translateY(-30px) scale(1.5); opacity: 1; } }
    @keyframes pulseText { from { opacity: 0.3; } to { opacity: 1; } }
    @keyframes thrust { from { height: 15px; opacity: 0.8; } to { height: 40px; opacity: 1; } }
    @keyframes spinEnemy { from { transform: rotateY(0deg) translateX(-50%); } to { transform: rotateY(360deg) translateX(-50%); } }
    @keyframes glitch { 0% { transform: translate(2px, 2px); } 20% { transform: translate(-2px, -2px); } 40% { transform: translate(-2px, 2px); } 60% { transform: translate(2px, -2px); } 80% { transform: translate(0, 0); } 100% { transform: translate(0, 0); } }
    @keyframes pulseReward { from { opacity: 0.8; filter: brightness(1); } to { opacity: 1; filter: brightness(1.5); } }
  `]
})
export class AppComponent {
  leapState = signal<'idle' | 'leaping'>('idle');
  particles = signal<Array<{ id: number, x: number, y: number, delay: number, color: string }>>([]);

  // Game State
  gameMode = signal<boolean>(false);
  isGameOver = signal<boolean>(false);
  is3D = signal<boolean>(true);
  score = signal<number>(0);
  level = signal<number>(1);

  // 3D & Movement state
  playerX = signal<number>(window.innerWidth / 2);
  shipTilt = signal<number>(0);
  cameraPan = signal<number>(0);

  lasers = signal<GameObject[]>([]);
  enemies = signal<GameObject[]>([]);
  explosions = signal<Explosion[]>([]);
  stars = signal<Star[]>([]);
  rewards = signal<GameObject[]>([]);
  boostActive = signal<boolean>(false);
  shieldActive = signal<boolean>(false);
  private boostEndTime = 0;

  private gameLoopRef: any;
  private keys: Set<string> = new Set();
  private lastShot = 0;
  private objIdCounter = 0;

  constructor() {
    this.generateParticles(50);
  }

  generateParticles(count: number) {
    const colors = ['#0ff', '#f0f', '#0f0', '#fff'];
    const newParticles = Array.from({ length: count }, (_, i) => ({
      id: Math.random(), x: Math.random() * 100, y: Math.random() * 100, delay: Math.random() * 2, color: colors[Math.floor(Math.random() * colors.length)]
    }));
    this.particles.set(newParticles);
  }

  initiateLeap() {
    if (this.leapState() === 'leaping') return;
    this.particles.set([]);
    this.leapState.set('leaping');

    setTimeout(() => {
      this.gameMode.set(true);
      this.initStars();
      this.startGame();
    }, 2500);
  }

  initStars() {
    // Generate stars with depth (smaller stars are further back and move slower)
    const initialStars = Array.from({ length: 150 }, () => {
      const size = Math.random() * 3 + 1;
      return {
        x: Math.random() * (window.innerWidth * 1.2),
        y: Math.random() * (window.innerHeight * 1.2),
        speed: size * 1.5,
        size: size
      };
    });
    this.stars.set(initialStars);
  }

  @HostListener('window:keydown', ['$event'])
  onKeyDown(e: KeyboardEvent) {
    this.keys.add(e.code);
    if (this.gameMode() && e.code === 'Escape') this.abortGame();
    if (this.gameMode() && e.code === 'KeyV') this.is3D.set(!this.is3D());
    if (this.isGameOver() && (e.code === 'KeyR' || e.code === 'Enter')) this.startGame();
  }

  @HostListener('window:keyup', ['$event'])
  onKeyUp(e: KeyboardEvent) {
    this.keys.delete(e.code);
  }

  startGame() {
    this.isGameOver.set(false);
    this.score.set(0);
    this.level.set(1);
    this.playerX.set(window.innerWidth / 2);
    this.shipTilt.set(0);
    this.cameraPan.set(0);
    this.lasers.set([]);
    this.enemies.set([]);
    this.explosions.set([]);
    this.rewards.set([]);
    this.boostActive.set(false);
    this.shieldActive.set(false);
    this.boostEndTime = 0;
    if (this.gameLoopRef) cancelAnimationFrame(this.gameLoopRef);
    this.gameLoopRef = requestAnimationFrame(() => this.gameLoop());
  }

  abortGame() {
    cancelAnimationFrame(this.gameLoopRef);
    this.gameMode.set(false);
    this.leapState.set('idle');
    this.generateParticles(50);
  }

  createExplosion(x: number, y: number, color: string) {
    const expParticles = Array.from({ length: 15 }, () => {
      const angle = Math.random() * Math.PI * 2;
      const speed = Math.random() * 12 + 3;
      return { x: 0, y: 0, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life: 1, color };
    });
    this.explosions.update(exps => [...exps, { id: ++this.objIdCounter, x, y, particles: expParticles }]);
  }

  gameLoop() {
    if (!this.gameMode()) return;
    if (this.isGameOver()) {
      this.animateBackground();
      // Decay tilt and pan on game over
      this.shipTilt.set(this.shipTilt() * 0.9);
      this.cameraPan.set(this.cameraPan() * 0.95);
      this.gameLoopRef = requestAnimationFrame(() => this.gameLoop());
      return;
    }

    this.animateBackground();

    // 3D Player Movement and Tilt
    let px = this.playerX();
    let tilt = this.shipTilt();
    const speed = 10 + (this.level() * 0.5);

    if (this.keys.has('ArrowLeft') || this.keys.has('KeyA')) {
      px = Math.max(50, px - speed);
      tilt = Math.max(-50, tilt - 4); // Bank left
    } else if (this.keys.has('ArrowRight') || this.keys.has('KeyD')) {
      px = Math.min(window.innerWidth - 50, px + speed);
      tilt = Math.min(50, tilt + 4); // Bank right
    } else {
      // Auto-level
      tilt *= 0.85;
    }

    this.playerX.set(px);
    this.shipTilt.set(tilt);

    // Pan the camera based on player position for extreme 3D effect
    const center = window.innerWidth / 2;
    const offset = (px - center) / center; // -1 to 1
    this.cameraPan.set(offset * 25); // Max 25 degree camera rotation

    // Shooting
    const now = Date.now();
    const fireRate = this.boostActive() ? 60 : Math.max(100, 250 - (this.level() * 15));
    if (this.keys.has('Space') && now - this.lastShot > fireRate) {
      this.lasers.update(l => [...l, { id: ++this.objIdCounter, x: px, y: 60, width: 4, height: 20, active: true }]);
      if (this.level() >= 5 || this.boostActive()) {
        this.lasers.update(l => [
          ...l,
          { id: ++this.objIdCounter, x: px - 25, y: 50, width: 4, height: 20, active: true },
          { id: ++this.objIdCounter, x: px + 25, y: 50, width: 4, height: 20, active: true }
        ]);
      }
      this.lastShot = now;
    }

    // Update Lasers
    this.lasers.update(lasers => lasers.map(l => ({ ...l, y: l.y + 25 })).filter(l => l.y < window.innerHeight + 100 && l.active));

    // Spawn Enemies
    const spawnChance = Math.min(0.12, 0.03 + (this.level() * 0.008));
    if (Math.random() < spawnChance) {
      const isFast = Math.random() > 0.7 && this.level() > 2;
      this.enemies.update(e => [...e, {
        id: ++this.objIdCounter,
        x: Math.random() * (window.innerWidth - 100) + 50,
        y: window.innerHeight + 100,
        width: 30, height: 30,
        active: true,
        type: isFast ? 1 : 0,
        speedY: isFast ? (10 + this.level()) : (5 + (this.level() * 0.5)),
        speedX: isFast ? (Math.random() > 0.5 ? 3 : -3) : 0
      }]);
    }

    // Spawn Rewards
    if (Math.random() < 0.002) {
      this.rewards.update(r => [...r, {
        id: ++this.objIdCounter,
        x: Math.random() * (window.innerWidth - 100) + 50,
        y: window.innerHeight + 100,
        width: 50, height: 50,
        active: true,
        rewardType: Math.random() > 0.5 ? 1 : 0
      }]);
    }

    // Update Enemies & Collisions
    let currentScore = this.score();
    let currentLasers = this.lasers();
    let gameOver = false;

    this.enemies.update(enemies => {
      return enemies.map(enemy => {
        enemy.y -= enemy.speedY || 5;
        if (enemy.speedX) enemy.x += enemy.speedX;

        if (enemy.x < 30 || enemy.x > window.innerWidth - 30) enemy.speedX = -(enemy.speedX || 0);

        currentLasers.forEach(laser => {
          if (laser.active && enemy.active && Math.abs(laser.x - enemy.x) < 40 && Math.abs(laser.y - enemy.y) < 40) {
            enemy.active = false;
            laser.active = false;
            currentScore += enemy.type === 1 ? 200 : 100;
            this.createExplosion(enemy.x, enemy.y, enemy.type === 1 ? '#ff0' : '#f00');
          }
        });

        if (enemy.active && Math.abs(enemy.x - px) < 40 && enemy.y < 70) {
          if (this.shieldActive()) {
            this.shieldActive.set(false);
            enemy.active = false;
            this.createExplosion(px, 50, '#08f');
          } else {
            gameOver = true;
            this.createExplosion(px, 50, '#0ff');
            enemy.active = false;
          }
        }
        return enemy;
      }).filter(e => e.y > -100 && e.active);
    });

    // Update Rewards & Collisions
    let hitBoost = false;
    let hitShield = false;
    this.rewards.update(rewards => {
      return rewards.map(reward => {
        reward.y -= 4;
        if (reward.active && Math.abs(reward.x - px) < 50 && reward.y < 80) {
          reward.active = false;
          if (reward.rewardType === 1) hitShield = true;
          else hitBoost = true;
          this.createExplosion(px, 60, reward.rewardType === 1 ? '#08f' : '#0f0');
        }
        return reward;
      }).filter(r => r.y > -100 && r.active);
    });

    if (hitShield) {
      currentScore += 500;
      this.shieldActive.set(true);
    }
    if (hitBoost) {
      currentScore += 500;
      this.boostActive.set(true);
      this.boostEndTime = Date.now() + 5000;
    }
    if (this.boostActive() && Date.now() > this.boostEndTime) {
      this.boostActive.set(false);
    }

    this.score.set(currentScore);
    this.level.set(Math.floor(currentScore / 1000) + 1);
    this.lasers.set(currentLasers);

    if (gameOver) {
      this.isGameOver.set(true);
    }

    this.gameLoopRef = requestAnimationFrame(() => this.gameLoop());
  }

  animateBackground() {
    this.stars.update(s => s.map(star => {
      star.y -= star.speed;
      if (star.y < -50) {
        star.y = window.innerHeight + 50;
        star.x = Math.random() * (window.innerWidth * 1.2);
      }
      return star;
    }));

    this.explosions.update(exps => {
      return exps.map(exp => {
        exp.particles.forEach(p => { p.x += p.vx; p.y += p.vy; p.life -= 0.03; });
        return exp;
      }).filter(exp => exp.particles[0].life > 0);
    });
  }
}
