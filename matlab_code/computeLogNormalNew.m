function [W,L,sigma,nEval] = computeLogNormalNew(vecM)
% Function computing the parameters of the main quadrature of EQMOM for a
% multi-LogN reconstruction;
% Takes a vector of N moments as input and formulate a P nodes extended
% quadrature with P=(N-1)/2. N must be odd.
%
% >> [W,L,sigma,nEval] = computeLogNormalNew(vecM,fc)
%   *Inputs :
%      + vecM  : Vector of realizable moments     (N*1)[double]
%      + fc    : Instance of the flopCount class
%   *Outputs :
%      + W     : Row vector of KDF weights        (1*P)[double]
%      + L     : Column vector of KDF locations   (P*1)[double]
%      + sigma : Scalar value of spreading factor (1*1)[double]
%      + nEval : Number of evaluated sigma values (1*1)[uint32]
%
% If moments are unrealizable, the returned variables contain only NaN.

% == SOLVER PARAMETERS ==
nEvalMax = 100;
relTol   = 1e-10;
status   = 0;
nEval    = 0;

% == CHECKING INPUTS ==
N = numel(vecM);
if mod(N,2)==0 || size(vecM,2)~=1
    warning('Vector of moments has wrong dimensions.')
    status = 7;
elseif ~isnumeric(vecM) || ~isreal(vecM) || any(isnan(vecM) | ~isfinite(vecM))
    warning('Vector of moments is incorrectly defined.')
    status = 7;
end
if status == 7
    W = NaN; L = NaN; sigma = NaN; return;
end

% == VARIABLE INITIALISATION ==

P = .5*(N-1); 
A = zeros(P,4);
B = zeros(P,4);
S = zeros(N,P+1); S(1,1)=1;
Z = zeros(2*P,4);

p = [1 2 3 4 1 4 0];
s2 = [0 NaN NaN NaN];

% == PRECOMPUTATIONS ==
% -- Reduced moments --
M0 = vecM(1);
iM0 = 1/M0; 
MB = zeros(N-1,1);
for i=2:N
    MB(i-1) = vecM(i)*iM0; 
end

% == SEARCH INITIALIZATION ==

% -- Chebyshev algorithm with s = 0 --
for i=1:N-1
    S(i+1,1) = MB(i);
end
A(1,1) = MB(1);
Z(1,1) = MB(1);
for j=0:(N-3)
    S(j+2,2) = S(j+3,1)-A(1,1)*S(j+2,1);
    
end
B(1,1) = S(2,2)/S(1,1);
Z(2,1) = B(1,1)/Z(1,1);
A(2,1) = S(3,2)/S(2,2)-S(2,1)/S(1,1);
Z(3,1) = A(2,1) - Z(2,1);


for i=3:P
    for j = 0:(N+1-2*i)
        S(i+j,i) = S(i+j+1,i-1)-A(i-1,1)*S(i+j,i-1)-B(i-2,1)*S(i+j,i-2);
       
    end
    B(i-1,1) = S(i,i)/S(i-1,i-1);
    Z(2*i-2,1) = B(i-1,1)/Z(2*i-3,1);
    A(i,1) = S(i+1,i)/S(i,i)-S(i,i-1)/S(i-1,i-1);
    Z(2*i-1,1) = A(i,1)-Z(2*i-2,1);
   
end
S(P+1,P+1) = S(P+2,P)-A(P,1)*S(P+1,P)-B(P-1,1)*S(P+1,P-1);
B(P,1) = S(P+1,P+1)/S(P,P);
Z(2*P,1) = B(P,1)/Z(2*P-1,1);

nEval = nEval + 1; 

% -- Check realizability of raw moments --
for i=1:2*P
    if Z(i,1)<-relTol
        % - Unrealisable moments -
        status = 6; %#ok<NASGU>
        W = nan(1,P);
        L = nan(P,1);
        sigma = NaN;
        return;
    elseif Z(i,1)<relTol
        % - Degenerated moments -
        Z(i,1) = 0; %Purify value
        status = 3; break;
    end
end

% -- Chebyshev algorithm with s = smax --
if status==0
    
    s2(4) = log(MB(2)/(MB(1)*MB(1)));
   
    
   
    % - Degenerated moments -
    z=exp(-.5*s2(4)); zp=1; zp2=1;
    
    for i=1:N-1
        zp2=zp2*zp*zp*z;
        zp=zp*z;
        S(i+1,1)=MB(i)*zp2;
        
    end
    nEval = nEval + 1; 
    % - End degenerated moments -
    
    
    A(1,4) = S(2,1);
    Z(1,4) = A(1,4);
    for i=0:(N-3)
        S(i+2,2)=S(i+3,1)-A(1,4)*S(i+2,1);
       
    end
    B(1,4)=S(2,2)/S(1,1);
    Z(2,4)=B(1,4)/Z(1,4);
    A(2,4)=S(3,2)/S(2,2)-S(2,1)/S(1,1);
    Z(3,4) = A(2,4) - Z(2,4);
 
    for i=3:P
        for j=0:(N+1-2*i)
            S(i+j,i)=S(i+j+1,i-1)-A(i-1,4)*S(i+j,i-1)-B(i-2,4)*S(i+j,i-2);
           
        end
        B(i-1,4)=S(i,i)/S(i-1,i-1);
        Z(2*i-2,4) = B(i-1,4)/Z(2*i-3,4);
        A(i,4) = S(i+1,i)/S(i,i)-S(i,i-1)/S(i-1,i-1);
        Z(2*i-1,4) = A(i,4)-Z(2*i-2,4);
      
    end
    S(P+1,P+1)=S(P+2,P)-A(P,4)*S(P+1,P)-B(P-1,4)*S(P+1,P-1);
    B(P,4)=S(P+1,P+1)/S(P,P);
    Z(2*P,4) = B(P,4)/Z(2*P-1,4);
   
end

% == INTERMEDIATE SEARCH ==
Zref = Z(:,1)*relTol;
sref = s2(4)*relTol;

k=1;
while status==0 && k<2*P
    if Z(k,p(4))>0, k=k+1; continue, end
    
    % -- Reset pointers to next-bound candidates --
    p(5) = 1;
    p(6) = 4;
    
    % == First step of Ridder's method ==
    % -- Compute sigma value --
   
    s2(p(2)) = .5*(s2(p(1))+s2(p(4)));
    
  
    % -- Compute degenerated moments --
 
    z=exp(-.5*s2(p(2))); zp=1; zp2=1;
    for i=1:N-1
        zp2=zp2*zp*zp*z;
        zp=zp*z;
        S(i+1,1)=MB(i)*zp2;
    
    end
    nEval = nEval + 1; 
    
    % -- Chebyshev algorithm --
 
    A(1,p(2)) = S(2,1);
    Z(1,p(2)) = A(1,p(2));
    for i=0:(N-3)
        S(i+2,2)=S(i+3,1)-A(1,p(2))*S(i+2,1);
   
    end
    B(1,p(2)) = S(2,2)/S(1,1);
    Z(2,p(2)) = B(1,p(2))/Z(1,p(2));
    A(2,p(2)) = S(3,2)/S(2,2)-S(2,1)/S(1,1);
    Z(3,p(2)) = A(2,p(2)) - Z(2,p(2));
 
    for i=3:P
        for j=0:(N+1-2*i)
            S(i+j,i) = S(i+j+1,i-1)-A(i-1,p(2))*S(i+j,i-1)-B(i-2,p(2))*S(i+j,i-2);
          
        end
        B(i-1,p(2)) = S(i,i)/S(i-1,i-1);
        Z(2*i-2,p(2)) = B(i-1,p(2))/Z(2*i-3,p(2));
        A(i,p(2)) = S(i+1,i)/S(i,i)-S(i,i-1)/S(i-1,i-1);
        Z(2*i-1,p(2)) = A(i,p(2))-Z(2*i-2,p(2));
      
    end
    S(P+1,P+1) = S(P+2,P)-A(P,p(2))*S(P+1,P)-B(P-1,p(2))*S(P+1,P-1);
    B(P,p(2)) = S(P+1,P+1)/S(P,P);
    Z(2*P,p(2)) = B(P,p(2))/Z(2*P-1,p(2));
 
    
    % -- Arbitrate about the value s2(p(2)) --
    t1 = Z(k,p(2))>0;
    t2 = false;
    if t1
        for i=k+1:2*P, if Z(i,p(2))<0, t2=true; break; end, end
    end
    
    if t2
        % p(2) becomes the new right bound and we jump to the next iteration
        p(7) = p(4); p(4) = p(2); p(2) = p(7); continue;
    elseif t1
        % p(2) becomes candidate to be the next left bound
        p(5) = 2;
    else
        % p(2) becomes candidate to be the next right bound
        p(6) = 2;
    end
    
    % == Second step of Ridder's method ==
    % -- Compute sigma value --
  
    s2(p(3)) = s2(p(2)) + (s2(p(2))-s2(p(1)))*Z(k,p(2))/...
        sqrt(Z(k,p(2))*Z(k,p(2))-Z(k,p(1))*Z(k,p(4)));
   
    
    % -- Compute degenerated moments --
  
    z=exp(-.5*s2(p(3))); zp=1; zp2=1;
    for i=1:N-1
        zp2=zp2*zp*zp*z;
        zp=zp*z;
        S(i+1,1)=MB(i)*zp2;
        
    end
    nEval = nEval + 1; 
    
    % -- Chebyshev algorithm --
 
    A(1,p(3)) = S(2,1);
    Z(1,p(3)) = A(1,p(3));
    for i=0:(N-3)
        S(i+2,2)=S(i+3,1)-A(1,p(3))*S(i+2,1);
       
    end
    B(1,p(3)) = S(2,2)/S(1,1);
    Z(2,p(3)) = B(1,p(3))/Z(1,p(3));
    A(2,p(3)) = S(3,2)/S(2,2)-S(2,1)/S(1,1);
    Z(3,p(3)) = A(2,p(3)) - Z(2,p(3));
 
    for i=3:P
        for j=0:(N+1-2*i)
            S(i+j,i) = S(i+j+1,i-1)-A(i-1,p(3))*S(i+j,i-1)-B(i-2,p(3))*S(i+j,i-2);
         
        end
        B(i-1,p(3)) = S(i,i)/S(i-1,i-1);
        Z(2*i-2,p(3)) = B(i-1,p(3))/Z(2*i-3,p(3));
        A(i,p(3)) = S(i+1,i)/S(i,i)-S(i,i-1)/S(i-1,i-1);
        Z(2*i-1,p(3)) = A(i,p(3))-Z(2*i-2,p(3));
    
    end
    S(P+1,P+1) = S(P+2,P)-A(P,p(3))*S(P+1,P)-B(P-1,p(3))*S(P+1,P-1);
    B(P,p(3)) = S(P+1,P+1)/S(P,P);
    Z(2*P,p(3)) = B(P,p(3))/Z(2*P-1,p(3));
  
    
    % -- Arbitrate about the value s2(p(3)) --
    t1 = Z(k,p(3))>0;
    t2 = false;
    if t1
        for i=k+1:2*P, if Z(i,p(3))<0, t2=true; break; end, end
    end
    
    if ~t2 && t1 && s2(p(3))>s2(p(p(5)))
        % s2(p(3)) becomes candidate to be the next left bound
        p(5) = 3;
    end
    if ~t1 && s2(p(3))<s2(p(p(6)))
        % s2(p(3)) becomes candidate to be the next right bound
        p(6) = 3;
    end
    
    % == Apply new bounds ==
    p(7) = p(1); p(1) = p(p(5)); p(p(5)) = p(7);
    p(7) = p(4); p(4) = p(p(6)); p(p(6)) = p(7);
    
    % == Check partial convergence ==
    if s2(p(4))-s2(p(1))< sref, status = 1; break; end
    if nEval > nEvalMax, status = 5; break; end
end


% == FINAL SEARCH ==
while status == 0
    % -- Reset pointers to next-bound candidates --
    p(5) = 1;
    p(6) = 4;
    
    % == First step of Ridder's method ==
    % -- Compute sigma value --
  
    s2(p(2)) = .5*(s2(p(1))+s2(p(4)));
    
    % -- Compute degenerated moments --
  
    z=exp(-.5*s2(p(2))); zp=1; zp2=1;
    for i=1:N-1
        zp2=zp2*zp*zp*z;
        zp=zp*z;
        S(i+1,1)=MB(i)*zp2;
     
    end
   
    nEval = nEval + 1; 
    
    % -- Chebyshev algorithm --
 
    A(1,p(2)) = S(2,1);
    Z(1,p(2)) = A(1,p(2));
    for i=0:(N-3)
        S(i+2,2)=S(i+3,1)-A(1,p(2))*S(i+2,1);
  
    end
    B(1,p(2)) = S(2,2)/S(1,1);
    Z(2,p(2)) = B(1,p(2))/Z(1,p(2));
    A(2,p(2)) = S(3,2)/S(2,2)-S(2,1)/S(1,1);
    Z(3,p(2)) = A(2,p(2)) - Z(2,p(2));
 
    for i=3:P
        for j=0:(N+1-2*i)
            S(i+j,i) = S(i+j+1,i-1)-A(i-1,p(2))*S(i+j,i-1)-B(i-2,p(2))*S(i+j,i-2);
            
        end
        B(i-1,p(2)) = S(i,i)/S(i-1,i-1);
        Z(2*i-2,p(2)) = B(i-1,p(2))/Z(2*i-3,p(2));
        A(i,p(2)) = S(i+1,i)/S(i,i)-S(i,i-1)/S(i-1,i-1);
        Z(2*i-1,p(2)) = A(i,p(2))-Z(2*i-2,p(2));
     
    end
    S(P+1,P+1) = S(P+2,P)-A(P,p(2))*S(P+1,P)-B(P-1,p(2))*S(P+1,P-1);
    B(P,p(2)) = S(P+1,P+1)/S(P,P);
    Z(2*P,p(2)) = B(P,p(2))/Z(2*P-1,p(2));
    
    
    % -- Arbitrate about the value s2(p(2)) --
    if Z(2*P,p(2))>=0
        % p(2) becomes candidate to be the next left bound
        p(5) = 2;
    else
        % p(2) becomes candidate to be the next right bound
        p(6) = 2;
    end
    
    % == Second step of Ridder's method ==
    % -- Compute sigma value --
  
    
    s2(p(3)) = s2(p(2)) + (s2(p(2))-s2(p(1)))*Z(2*P,p(2))/...
        sqrt(Z(2*P,p(2))*Z(2*P,p(2))-Z(2*P,p(1))*Z(2*P,p(4)));
    
    % -- Compute degenerated moments --
   
    z=exp(-.5*s2(p(3))); zp=1; zp2=1;
    for i=1:N-1
        zp2=zp2*zp*zp*z;
        zp=zp*z;
        S(i+1,1)=MB(i)*zp2;
       
    end
   
    nEval = nEval + 1;
    
    % -- Chebyshev algorithm --
   
    A(1,p(3)) = S(2,1);
    Z(1,p(3)) = A(1,p(3));
    for i=0:(N-3)
        S(i+2,2)=S(i+3,1)-A(1,p(3))*S(i+2,1);
        
    end
    B(1,p(3)) = S(2,2)/S(1,1);
    Z(2,p(3)) = B(1,p(3))/Z(1,p(3));
    A(2,p(3)) = S(3,2)/S(2,2)-S(2,1)/S(1,1);
    Z(3,p(3)) = A(2,p(3)) - Z(2,p(3));
   
    for i=3:P
        for j=0:(N+1-2*i)
            S(i+j,i) = S(i+j+1,i-1)-A(i-1,p(3))*S(i+j,i-1)-B(i-2,p(3))*S(i+j,i-2);
           
        end
        B(i-1,p(3)) = S(i,i)/S(i-1,i-1);
        Z(2*i-2,p(3)) = B(i-1,p(3))/Z(2*i-3,p(3));
        A(i,p(3)) = S(i+1,i)/S(i,i)-S(i,i-1)/S(i-1,i-1);
        Z(2*i-1,p(3)) = A(i,p(3))-Z(2*i-2,p(3));
      
    end
    S(P+1,P+1) = S(P+2,P)-A(P,p(3))*S(P+1,P)-B(P-1,p(3))*S(P+1,P-1);
    B(P,p(3)) = S(P+1,P+1)/S(P,P);
    Z(2*P,p(3)) = B(P,p(3))/Z(2*P-1,p(3));
 
    % -- Arbitrate about the value s2(p(3)) --
    if Z(2*P,p(3))>=0 && s2(p(3))>s2(p(p(5)))
        p(5) = 3;
    elseif Z(2*P,p(3))<0 && s2(p(3))<s2(p(p(6)))
        p(6) = 3;
    end
    
    % == Apply new bounds ==
    p(7) = p(1); p(1) = p(p(5)); p(p(5)) = p(7);
    p(7) = p(4); p(4) = p(p(6)); p(p(6)) = p(7);
    
    % == Check convergence ==
    if Z(2*P,p(1))<Zref(2*P), Z(2*P,p(1))=0; status=1; break; end
    if s2(p(4))-s2(p(1))< sref, status = 1; break; end
    if nEval > nEvalMax, status = 5; break; end
end


% == QUADRATURE COMPUTATION ==
% -- Detect number of nodes --
n=2*P;
for i=1:2*P
    if Z(i,p(1))<=Zref(i)
        n=i; break;
    end
end
n = (n + mod(n,2))/2;


% -- Constructing Jacobi matrix --
J = zeros(n,n);
J(1,1) = A(1,p(1));
for i=2:n
    J(i,i) = A(i,p(1));
    J(i,i-1) = sqrt(B(i-1,p(1))); 
    J(i-1,i) = J(i,i-1);
end

% -- Computing weights and nodes --
sigma = sqrt(s2(p(1))); 
if n<4 %function_handle to eigenvalues computation function
    eigen=@eigenJacobi;% possible choices: @eigenJacobi and @eigenFrancis
else
    eigen=@eigenFrancis;
end

if n==P
    [W,L] = eigen(A(:,p(1)),B(1:P-1,p(1)));
  
    W=W*M0; 
else
    [w,l] = eigen(A(1:n,p(1)),B(1:n-1,p(1)));
    L=[l;.5*ones(P-n,1)];
    W=[w*M0 zeros(1,P-n)];
    status = status + 1;
end

end