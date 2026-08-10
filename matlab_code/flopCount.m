classdef flopCount < handle
  % This class is used to count the number of floating point operations.
  % Values are stored in a structure-array.
  % Each line correspond to a category of operation (in the present
  % context, a line is attributed to the EQMOM linear system, one to the
  % Chebyshev algorithm, one to the quadrature computaiton, and another one
  % for all other computations).
  % Each column corresponds to a moment set.
  % Each structure field correspond to an floating point operation (plus,
  % minus, times, divide, sqrt, abs or exp).
  %
  % The method obj.move(i) moves the storage pointer to the i-th line of
  % the array.
  % The method obj.next moves the storage pointer to the next column.
  % The methods obj.aop(i) allows to increment the counter associated to
  % 'op' by a value of i. obj.aop increments by one.
  %
  % The method obj.extract() returns a array giving the total number of
  % operation for each line and column of the stucture array.
  % Operations are unweighted.

  
  properties
    counter = struct('plus',0,'minus',0,'times',0,'divide',0,...
      'sqrt',0,'abs',0,'exp',0,'log',0,'gamma',0);
    indx = 1;
    indy = 1;
    maxIndx = 1;
    maxIndy = 1;
  end
  
  methods
    function obj = flopCount()
      
    end
    function add(obj,name,num)
      if nargin==2
        obj.counter.(name)(obj.indx,obj.indy) = obj.counter.(name)(obj.indx,obj.indy) + 1;
      else
        obj.counter.(name)(obj.indx,obj.indy) = obj.counter.(name)(obj.indx,obj.indy) + num;
      end
    end
    function move(obj,dest)
      if nargin==1
        obj.indx = obj.indx+1;
      else
        obj.indx = dest;
      end
      if obj.indx > obj.maxIndx
        obj.maxIndx = obj.indx;
        lf = fieldnames(obj.counter);
        for i=1:numel(lf)
          obj.counter.(lf{i})(obj.indx,obj.maxIndy)=0;
        end        
      end
    end
    function next(obj)
      obj.indy = obj.indy+1;
      if obj.indy > obj.maxIndy
        obj.maxIndy = obj.indy;
        lf = fieldnames(obj.counter);
        for i=1:numel(lf)
          obj.counter.(lf{i})(obj.maxIndx,obj.indy)=0;
        end        
      end
    end
    function r=get(obj)
      r=obj.counter;
    end
  end
  
  
  methods
    function aplus(obj,varargin)
      obj.add('plus',varargin{:});
    end
    function aminus(obj,varargin)
      obj.add('minus',varargin{:});
    end
    function atimes(obj,varargin)
      obj.add('times',varargin{:});
    end
    function adiv(obj,varargin)
      obj.add('divide',varargin{:});
    end
    function asqrt(obj,varargin)
      obj.add('sqrt',varargin{:});
    end
    function aabs(obj,varargin)
      obj.add('abs',varargin{:});
    end
    function aexp(obj,varargin)
      obj.add('exp',varargin{:});
    end
    function alog(obj,varargin)
      obj.add('log',varargin{:});
    end
    function agamma(obj,varargin)
      obj.add('gamma',varargin{:});
    end
  end
  
  methods
    function r=extract(obj)
      r=obj.counter.plus + ...
        obj.counter.minus + ...
        obj.counter.times + ...
        obj.counter.divide + ...
        obj.counter.sqrt + ...
        obj.counter.abs + ...
        obj.counter.exp + ...
        obj.counter.log + ...
        obj.counter.gamma;
      r(end+1,:) = sum(r,1);
      r(:,end)=[];
    end
  end
end

